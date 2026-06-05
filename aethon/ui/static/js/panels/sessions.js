/**
 * AETHON Dashboard — Session Browser Panel
 *
 * Lists active sessions, shows session details.
 * Fetches from /api/sessions, auto-refreshes via telemetry events.
 */

import { esc, formatTime, fetchJSON } from '../theme.js';
import { ws } from '../ws.js';

let containerEl = null;
let unsubMessages = null;
let sessions = [];
let selectedSession = null;
let refreshTimer = null;

export function mount(container) {
  containerEl = container;
  sessions = [];
  selectedSession = null;
  _render();
  _fetchSessions();

  // Auto-refresh on new messages
  unsubMessages = ws.subscribe('messages', () => {
    _fetchSessions();
  });

  // Periodic refresh
  refreshTimer = setInterval(_fetchSessions, 15000);
}

export function unmount() {
  if (unsubMessages) {
    unsubMessages();
    unsubMessages = null;
  }
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2630</span>
        Session Browser
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="session-count">0 sessions</span>
        <button class="btn btn-sm btn-ghost" id="session-refresh" aria-label="Refresh sessions">\u21BB Refresh</button>
      </div>
    </div>

    <!-- Session layout: list + detail -->
    <div class="session-layout" id="session-layout">
      <!-- Session list -->
      <div class="glass-card" style="padding:0;overflow-y:auto;max-height:calc(100vh - 240px)">
        <div id="session-list">
          <div class="empty-state">
            <div class="empty-icon">\u2630</div>
            <div class="empty-text">Loading sessions...</div>
          </div>
        </div>
      </div>

      <!-- Session detail -->
      <div class="glass-card" id="session-detail" style="display:none">
        <div id="session-detail-content"></div>
      </div>
    </div>
  `;

  // Event listeners
  containerEl.querySelector('#session-refresh').addEventListener('click', () => {
    _fetchSessions();
  });
}

async function _fetchSessions() {
  try {
    const data = await fetchJSON('/api/sessions');
    sessions = data.sessions || [];
    _renderSessionList();
  } catch (e) {
    console.error('[Sessions] Fetch error:', e);
  }
}

function _renderSessionList() {
  const listEl = containerEl ? containerEl.querySelector('#session-list') : null;
  const countEl = containerEl ? containerEl.querySelector('#session-count') : null;
  if (!listEl) return;

  if (countEl) {
    countEl.textContent = `${sessions.length} session${sessions.length !== 1 ? 's' : ''}`;
  }

  if (sessions.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u2630</div>
        <div class="empty-text">No active sessions</div>
        <div class="empty-sub">Sessions will appear when users connect</div>
      </div>
    `;
    return;
  }

  listEl.innerHTML = sessions.map(s => {
    const parts = s.session_id.split(':');
    const channel = parts[0] || 'unknown';
    const sender = parts.slice(1).join(':') || 'unknown';
    const isSelected = selectedSession === s.session_id;
    const channelIcon = _channelIcon(channel);

    return `
      <div class="session-row ${isSelected ? 'selected' : ''}" data-sid="${esc(s.session_id)}">
        <div class="session-row-icon">${channelIcon}</div>
        <div class="session-row-info">
          <div class="session-row-id text-mono">${esc(s.session_id)}</div>
          <div class="session-row-meta">
            <span class="badge badge-info">${esc(channel)}</span>
            <span class="text-muted text-sm">${esc(s.agent_name || 'AETHON')}</span>
          </div>
        </div>
        <div class="session-row-status">
          <span class="status-dot status-active"></span>
        </div>
      </div>
    `;
  }).join('');

  // Click to select
  listEl.querySelectorAll('.session-row').forEach(row => {
    row.addEventListener('click', () => {
      selectedSession = row.dataset.sid;
      _renderSessionList();
      _showSessionDetail(selectedSession);
    });
  });
}

async function _showSessionDetail(sessionId) {
  const detailEl = containerEl ? containerEl.querySelector('#session-detail') : null;
  const contentEl = containerEl ? containerEl.querySelector('#session-detail-content') : null;
  if (!detailEl || !contentEl) return;

  detailEl.style.display = 'block';

  try {
    const data = await fetchJSON(`/api/sessions/${encodeURIComponent(sessionId)}`);

    if (data.error) {
      contentEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">\u26A0</div>
          <div class="empty-text">${esc(data.error)}</div>
        </div>
      `;
      return;
    }

    contentEl.innerHTML = `
      <h3 style="margin:0 0 16px 0;color:var(--accent-primary)">\u2726 Session Details</h3>
      <div class="detail-grid">
        <div class="detail-item">
          <span class="detail-label">Session ID</span>
          <span class="detail-value text-mono">${esc(data.session_id)}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Agent</span>
          <span class="detail-value">${esc(data.agent_name || 'AETHON')}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Channel</span>
          <span class="detail-value"><span class="badge badge-info">${esc(data.channel)}</span></span>
        </div>
        <div class="detail-item">
          <span class="detail-label">Sender</span>
          <span class="detail-value text-mono">${esc(data.sender)}</span>
        </div>
      </div>
    `;
  } catch (e) {
    contentEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u26A0</div>
        <div class="empty-text">Failed to load session details</div>
      </div>
    `;
  }
}

function _channelIcon(channel) {
  const icons = {
    webchat: '\u{1F4AC}',
    cli: '\u{1F4BB}',
    telegram: '\u{2708}',
    discord: '\u{1F3AE}',
    slack: '\u{1F4E8}',
    whatsapp: '\u{1F4F1}',
  };
  return icons[channel.toLowerCase()] || '\u{1F50C}';
}
