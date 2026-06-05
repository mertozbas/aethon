/**
 * AETHON Dashboard — Live Chat Monitor Panel
 *
 * Real-time message stream from all channels via WebSocket.
 * Channel filter tabs, user/bot distinction, session linking.
 */

import { esc, formatTime } from '../theme.js';
import { ws } from '../ws.js';
import { renderMarkdown } from '../components/markdown.js';

const CHANNELS = ['All', 'CLI', 'WebChat', 'Telegram', 'Discord', 'Slack', 'WhatsApp'];
const MAX_MESSAGES = 200;

let containerEl = null;
let unsubMessages = null;
let activeFilter = 'All';
let messages = [];
let autoScroll = true;

export function mount(container) {
  containerEl = container;
  messages = [];
  activeFilter = 'All';
  autoScroll = true;
  _render();

  // Subscribe to messages channel
  unsubMessages = ws.subscribe('messages', (data) => {
    _addMessage(data);
  });
}

export function unmount() {
  if (unsubMessages) {
    unsubMessages();
    unsubMessages = null;
  }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u25C9</span>
        Live Monitor
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <button class="btn btn-sm btn-ghost" id="monitor-clear" aria-label="Clear messages">\u2716 Clear</button>
        <button class="btn btn-sm ${autoScroll ? 'btn-primary' : 'btn-ghost'}" id="monitor-autoscroll" aria-label="Toggle auto-scroll">
          \u2193 Auto-scroll
        </button>
      </div>
    </div>

    <!-- Channel filter tabs -->
    <div class="filter-bar" id="monitor-filters">
      ${CHANNELS.map(ch => `
        <button class="filter-chip ${ch === activeFilter ? 'active' : ''}" data-channel="${ch}">${ch}</button>
      `).join('')}
    </div>

    <!-- Search -->
    <div style="margin-bottom:12px">
      <input class="input-field" id="monitor-search" placeholder="Search messages (regex supported)..." aria-label="Search messages">
    </div>

    <!-- Message stream -->
    <div class="glass-card" style="padding:0;max-height:calc(100vh - 280px);overflow-y:auto" id="monitor-stream">
      <div id="monitor-messages">
        <div class="empty-state">
          <div class="empty-icon">\u25C9</div>
          <div class="empty-text">Waiting for messages...</div>
          <div class="empty-sub">Send a message in WebChat to see it here in real-time</div>
        </div>
      </div>
    </div>
  `;

  // Event listeners
  containerEl.querySelector('#monitor-filters').addEventListener('click', (e) => {
    const chip = e.target.closest('.filter-chip');
    if (chip) {
      activeFilter = chip.dataset.channel;
      _updateFilters();
      _renderMessages();
    }
  });

  containerEl.querySelector('#monitor-clear').addEventListener('click', () => {
    messages = [];
    _renderMessages();
  });

  containerEl.querySelector('#monitor-autoscroll').addEventListener('click', (e) => {
    autoScroll = !autoScroll;
    e.currentTarget.className = `btn btn-sm ${autoScroll ? 'btn-primary' : 'btn-ghost'}`;
  });

  containerEl.querySelector('#monitor-search').addEventListener('input', (e) => {
    _renderMessages(e.target.value);
  });

  // Detect manual scroll
  const streamEl = containerEl.querySelector('#monitor-stream');
  if (streamEl) {
    streamEl.addEventListener('scroll', () => {
      const atBottom = streamEl.scrollHeight - streamEl.scrollTop - streamEl.clientHeight < 30;
      if (!atBottom && autoScroll) {
        // User scrolled up — pause auto-scroll visually but keep setting
      }
    });
  }
}

function _addMessage(data) {
  messages.push(data);
  if (messages.length > MAX_MESSAGES) {
    messages.shift();
  }
  _renderMessages();
}

function _updateFilters() {
  if (!containerEl) return;
  const chips = containerEl.querySelectorAll('.filter-chip');
  chips.forEach(chip => {
    chip.classList.toggle('active', chip.dataset.channel === activeFilter);
  });
}

function _renderMessages(searchQuery) {
  const messagesEl = containerEl ? containerEl.querySelector('#monitor-messages') : null;
  if (!messagesEl) return;

  let filtered = messages;

  // Channel filter
  if (activeFilter !== 'All') {
    const filterLower = activeFilter.toLowerCase();
    filtered = filtered.filter(m => {
      const ch = (m.channel_name || '').toLowerCase();
      return ch === filterLower || ch.includes(filterLower);
    });
  }

  // Search filter
  if (searchQuery) {
    try {
      const re = new RegExp(searchQuery, 'i');
      filtered = filtered.filter(m =>
        re.test(m.content || '') || re.test(m.sender || '') || re.test(m.channel_name || '')
      );
    } catch (e) {
      // Invalid regex — ignore
    }
  }

  if (filtered.length === 0) {
    messagesEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u25C9</div>
        <div class="empty-text">${messages.length === 0 ? 'Waiting for messages...' : 'No matching messages'}</div>
        <div class="empty-sub">${messages.length === 0 ? 'Send a message in WebChat to see it here in real-time' : 'Try a different filter or search query'}</div>
      </div>
    `;
    return;
  }

  messagesEl.innerHTML = filtered.map(m => {
    const isBot = m.direction === 'outbound' || m.sender === 'AETHON';
    const avatarClass = isBot ? 'bot' : 'user';
    const avatarIcon = isBot ? '\u2726' : '\u263A';
    const time = m.timestamp ? formatTime(new Date(m.timestamp * 1000)) : '--:--';
    const channel = esc(m.channel_name || 'unknown');
    const sender = esc(m.sender || (isBot ? 'AETHON' : 'User'));
    const content = isBot ? renderMarkdown(m.content || '') : esc(m.content || '');

    return `
      <div class="chat-msg">
        <div class="msg-avatar ${avatarClass}">${avatarIcon}</div>
        <div class="msg-body">
          <div class="msg-header">
            <span class="msg-sender" style="color:${isBot ? 'var(--color-success)' : 'var(--accent-primary)'}">${sender}</span>
            <span class="msg-channel">${channel}</span>
            <span class="msg-time">${time}</span>
          </div>
          <div class="msg-content">${content}</div>
        </div>
      </div>
    `;
  }).join('');

  // Auto-scroll to bottom
  if (autoScroll) {
    const streamEl = containerEl.querySelector('#monitor-stream');
    if (streamEl) {
      streamEl.scrollTop = streamEl.scrollHeight;
    }
  }
}
