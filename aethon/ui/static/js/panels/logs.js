/**
 * AETHON Dashboard — Log Viewer Panel
 *
 * Real-time log stream from Python logging via WebSocket.
 * Level & module filters, auto-scroll with pause, color-coded levels.
 */

import { esc, formatTime } from '../theme.js';
import { ws } from '../ws.js';

const LEVELS = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const MODULES = ['All', 'agent', 'gateway', 'router', 'dashboard', 'telemetry', 'runtime', 'memory', 'tools', 'channels'];
const MAX_LOGS = 500;

let containerEl = null;
let unsubLogs = null;
let activeLevel = 'ALL';
let activeModule = 'All';
let logs = [];
let autoScroll = true;

export function mount(container) {
  containerEl = container;
  logs = [];
  activeLevel = 'ALL';
  activeModule = 'All';
  autoScroll = true;
  _render();

  // Subscribe to logs channel
  unsubLogs = ws.subscribe('logs', (data) => {
    _addLog(data);
  });
}

export function unmount() {
  if (unsubLogs) {
    unsubLogs();
    unsubLogs = null;
  }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2261</span>
        Log Viewer
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="log-count">0 entries</span>
        <button class="btn btn-sm btn-ghost" id="log-clear" aria-label="Clear logs">\u2716 Clear</button>
        <button class="btn btn-sm ${autoScroll ? 'btn-primary' : 'btn-ghost'}" id="log-autoscroll" aria-label="Toggle auto-scroll">
          \u2193 Auto
        </button>
      </div>
    </div>

    <!-- Filters row -->
    <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
      <!-- Level filter -->
      <div style="display:flex;align-items:center;gap:6px">
        <span class="text-sm text-muted">Level:</span>
        <select class="input-field" id="log-level-filter" style="width:auto;padding:6px 30px 6px 10px" aria-label="Filter by log level">
          ${LEVELS.map(l => `<option value="${l}" ${l === activeLevel ? 'selected' : ''}>${l}</option>`).join('')}
        </select>
      </div>

      <!-- Module filter -->
      <div style="display:flex;align-items:center;gap:6px">
        <span class="text-sm text-muted">Module:</span>
        <select class="input-field" id="log-module-filter" style="width:auto;padding:6px 30px 6px 10px" aria-label="Filter by module">
          ${MODULES.map(m => `<option value="${m}" ${m === activeModule ? 'selected' : ''}>${m}</option>`).join('')}
        </select>
      </div>

      <!-- Search -->
      <div style="flex:1;min-width:180px">
        <input class="input-field" id="log-search" placeholder="Search logs..." style="margin:0" aria-label="Search logs">
      </div>
    </div>

    <!-- Log stream -->
    <div class="glass-card" style="padding:0;max-height:calc(100vh - 280px);overflow-y:auto;background:rgba(0,0,0,0.3)" id="log-stream">
      <div id="log-entries">
        <div class="empty-state">
          <div class="empty-icon">\u2261</div>
          <div class="empty-text">Waiting for log entries...</div>
          <div class="empty-sub">Logs will appear here as AETHON processes requests</div>
        </div>
      </div>
    </div>
  `;

  // Event listeners
  containerEl.querySelector('#log-level-filter').addEventListener('change', (e) => {
    activeLevel = e.target.value;
    _renderLogs();
  });

  containerEl.querySelector('#log-module-filter').addEventListener('change', (e) => {
    activeModule = e.target.value;
    _renderLogs();
  });

  containerEl.querySelector('#log-search').addEventListener('input', () => {
    _renderLogs();
  });

  containerEl.querySelector('#log-clear').addEventListener('click', () => {
    logs = [];
    _renderLogs();
  });

  containerEl.querySelector('#log-autoscroll').addEventListener('click', (e) => {
    autoScroll = !autoScroll;
    e.currentTarget.className = `btn btn-sm ${autoScroll ? 'btn-primary' : 'btn-ghost'}`;
  });
}

function _addLog(data) {
  logs.push(data);
  if (logs.length > MAX_LOGS) {
    logs.shift();
  }
  _renderLogs();
}

function _renderLogs() {
  const entriesEl = containerEl ? containerEl.querySelector('#log-entries') : null;
  const countEl = containerEl ? containerEl.querySelector('#log-count') : null;
  if (!entriesEl) return;

  let filtered = logs;

  // Level filter
  if (activeLevel !== 'ALL') {
    const levelOrder = { DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3, CRITICAL: 4 };
    const minLevel = levelOrder[activeLevel] || 0;
    filtered = filtered.filter(l => {
      const lv = levelOrder[l.level] !== undefined ? levelOrder[l.level] : 0;
      return lv >= minLevel;
    });
  }

  // Module filter
  if (activeModule !== 'All') {
    const mod = activeModule.toLowerCase();
    filtered = filtered.filter(l => {
      const logMod = (l.module || l.logger || '').toLowerCase();
      return logMod === mod || logMod.includes(mod);
    });
  }

  // Search filter
  const searchEl = containerEl ? containerEl.querySelector('#log-search') : null;
  const searchQuery = searchEl ? searchEl.value.trim() : '';
  if (searchQuery) {
    try {
      const re = new RegExp(searchQuery, 'i');
      filtered = filtered.filter(l =>
        re.test(l.message || '') || re.test(l.module || '') || re.test(l.level || '')
      );
    } catch (e) { /* invalid regex */ }
  }

  if (countEl) {
    countEl.textContent = `${filtered.length} / ${logs.length} entries`;
  }

  if (filtered.length === 0) {
    entriesEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u2261</div>
        <div class="empty-text">${logs.length === 0 ? 'Waiting for log entries...' : 'No matching logs'}</div>
        <div class="empty-sub">${logs.length === 0 ? 'Logs will appear here as AETHON processes requests' : 'Adjust filters to see more entries'}</div>
      </div>
    `;
    return;
  }

  entriesEl.innerHTML = filtered.map(l => {
    const level = (l.level || 'INFO').toUpperCase();
    const levelClass = `log-level-${level.toLowerCase()}`;
    const time = l.timestamp ? formatTime(l.timestamp) : '--:--:--';
    const module = esc(l.module || 'root');
    const msg = esc(l.message || '');

    return `<div class="log-entry">
      <span class="log-time">${time}</span>
      <span class="log-level ${levelClass}">${level}</span>
      <span class="log-module">${module}</span>
      <span class="log-msg">${_highlightSearch(msg, searchQuery)}</span>
    </div>`;
  }).join('');

  // Auto-scroll
  if (autoScroll) {
    const streamEl = containerEl.querySelector('#log-stream');
    if (streamEl) {
      streamEl.scrollTop = streamEl.scrollHeight;
    }
  }
}

function _highlightSearch(text, query) {
  if (!query) return text;
  try {
    const re = new RegExp(`(${query})`, 'gi');
    return text.replace(re, '<mark style="background:rgba(0,212,255,0.25);color:var(--accent-primary);border-radius:2px;padding:0 2px">$1</mark>');
  } catch (e) {
    return text;
  }
}
