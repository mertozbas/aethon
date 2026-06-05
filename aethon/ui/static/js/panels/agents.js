/**
 * AETHON Dashboard — Agent Activity Panel
 *
 * Real-time agent activity visualization.
 * Shows active agents, tool calls, model calls as timeline events.
 * Subscribes to 'agents' and 'telemetry' WebSocket channels.
 */

import { esc, formatTime, formatDuration, fetchJSON } from '../theme.js';
import { ws } from '../ws.js';

const MAX_EVENTS = 100;

let containerEl = null;
let unsubAgents = null;
let unsubTelemetry = null;
let agents = [];
let events = [];
let refreshTimer = null;

export function mount(container) {
  containerEl = container;
  agents = [];
  events = [];
  _render();
  _fetchAgents();
  _fetchHistory();

  // Subscribe to real-time agent events
  unsubAgents = ws.subscribe('agents', (data) => {
    _addEvent(data);
  });

  unsubTelemetry = ws.subscribe('telemetry', (data) => {
    _addEvent(data);
  });

  // Periodic agent list refresh
  refreshTimer = setInterval(_fetchAgents, 10000);
}

export function unmount() {
  if (unsubAgents) { unsubAgents(); unsubAgents = null; }
  if (unsubTelemetry) { unsubTelemetry(); unsubTelemetry = null; }
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2726</span>
        Agent Activity
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="agent-count">-</span>
        <button class="btn btn-sm btn-ghost" id="agent-clear" aria-label="Clear events">\u2716 Clear</button>
        <button class="btn btn-sm btn-ghost" id="agent-refresh" aria-label="Refresh">\u21BB</button>
      </div>
    </div>

    <!-- Active agents -->
    <div id="agent-cards" class="summary-grid" style="margin-bottom:16px"></div>

    <!-- Activity timeline -->
    <div class="glass-card" style="padding:0;max-height:calc(100vh - 360px);overflow-y:auto" id="agent-timeline-container">
      <div id="agent-timeline">
        <div class="empty-state">
          <div class="empty-icon">\u2726</div>
          <div class="empty-text">Waiting for agent activity...</div>
          <div class="empty-sub">Tool calls and model calls will appear here in real-time</div>
        </div>
      </div>
    </div>
  `;

  containerEl.querySelector('#agent-refresh').addEventListener('click', () => {
    _fetchAgents();
    _fetchHistory();
  });

  containerEl.querySelector('#agent-clear').addEventListener('click', () => {
    events = [];
    _renderTimeline();
  });
}

async function _fetchAgents() {
  try {
    const data = await fetchJSON('/api/agents/active');
    agents = data.agents || [];
    const countEl = containerEl ? containerEl.querySelector('#agent-count') : null;
    if (countEl) countEl.textContent = `${agents.length} agent${agents.length !== 1 ? 's' : ''}`;
    _renderAgentCards();
  } catch (e) {
    console.error('[Agents] Fetch error:', e);
  }
}

async function _fetchHistory() {
  try {
    const data = await fetchJSON('/api/agents/history');
    const history = data.events || [];
    // Prepend history to events (avoid duplicates)
    if (history.length > 0 && events.length === 0) {
      events = history.slice(-MAX_EVENTS);
      _renderTimeline();
    }
  } catch (e) {
    console.error('[Agents] History error:', e);
  }
}

function _addEvent(data) {
  events.push(data);
  if (events.length > MAX_EVENTS) events.shift();
  _renderTimeline();
}

function _renderAgentCards() {
  const cardsEl = containerEl ? containerEl.querySelector('#agent-cards') : null;
  if (!cardsEl) return;

  if (agents.length === 0) {
    cardsEl.innerHTML = `
      <div class="summary-card" style="grid-column:1/-1">
        <div class="card-value text-muted">No active agents</div>
        <div class="card-label">Agents will appear when sessions are active</div>
      </div>
    `;
    return;
  }

  cardsEl.innerHTML = agents.map(a => {
    const parts = a.session_id.split(':');
    const channel = parts[0] || '';
    return `
      <div class="summary-card">
        <div class="card-icon" style="color:var(--color-success)">\u2726</div>
        <div class="card-value">${esc(a.agent_name || 'AETHON')}</div>
        <div class="card-label">
          <span class="badge badge-info">${esc(channel)}</span>
          <span class="text-mono text-sm">${esc(a.agent_id || 'main')}</span>
        </div>
      </div>
    `;
  }).join('');
}

function _renderTimeline() {
  const timelineEl = containerEl ? containerEl.querySelector('#agent-timeline') : null;
  if (!timelineEl) return;

  if (events.length === 0) {
    timelineEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u2726</div>
        <div class="empty-text">Waiting for agent activity...</div>
        <div class="empty-sub">Tool calls and model calls will appear here in real-time</div>
      </div>
    `;
    return;
  }

  // Render most recent events at bottom
  timelineEl.innerHTML = events.map(e => {
    const isAgent = e.event !== undefined;
    const isTool = e.type === 'tool';
    const isModel = e.type === 'model';

    if (isAgent) {
      return _renderAgentEvent(e);
    } else if (isTool) {
      return _renderToolEvent(e);
    } else if (isModel) {
      return _renderModelEvent(e);
    }

    return '';
  }).join('');

  // Auto-scroll to bottom
  const container = containerEl.querySelector('#agent-timeline-container');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function _renderAgentEvent(e) {
  const isStart = e.event === 'tool_start';
  const icon = isStart ? '\u25B6' : '\u2714';
  const color = isStart ? 'var(--accent-primary)' : 'var(--color-success)';
  const time = e.timestamp ? formatTime(e.timestamp) : '--:--';

  return `
    <div class="log-entry" style="border-left:3px solid ${color}">
      <span class="log-time">${time}</span>
      <span style="color:${color};font-weight:600;min-width:20px">${icon}</span>
      <span class="text-sm" style="color:${color}">${esc(e.event)}</span>
      <span class="badge badge-ghost">${esc(e.tool_name || '')}</span>
      ${e.duration !== undefined ? `<span class="text-mono text-sm text-muted">${formatDuration(e.duration)}</span>` : ''}
      ${e.status && e.status !== 'success' ? `<span class="badge badge-error">${esc(e.status)}</span>` : ''}
    </div>
  `;
}

function _renderToolEvent(e) {
  const statusColor = e.status === 'success' ? 'var(--color-success)' :
                      e.status === 'error' ? 'var(--color-error)' : 'var(--color-warning)';
  const time = e.timestamp ? formatTime(e.timestamp) : '--:--';

  return `
    <div class="log-entry">
      <span class="log-time">${time}</span>
      <span class="badge badge-info">TOOL</span>
      <span class="text-sm" style="font-weight:500">${esc(e.name || '')}</span>
      <span class="text-mono text-sm" style="color:${statusColor}">${formatDuration(e.duration)}</span>
      <span class="text-mono text-sm" style="color:${statusColor}">${esc(e.status || '')}</span>
    </div>
  `;
}

function _renderModelEvent(e) {
  const time = e.timestamp ? formatTime(e.timestamp) : '--:--';
  const stopReason = e.extra?.stop_reason || '';

  return `
    <div class="log-entry">
      <span class="log-time">${time}</span>
      <span class="badge badge-warning">MODEL</span>
      <span class="text-mono text-sm">${formatDuration(e.duration)}</span>
      ${stopReason ? `<span class="text-sm text-muted">${esc(stopReason)}</span>` : ''}
    </div>
  `;
}
