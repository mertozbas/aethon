/**
 * AETHON Dashboard — Overview Panel
 *
 * Summary cards showing sessions, memory, telemetry, scheduler stats.
 * Fetches from existing /api/* REST endpoints.
 * Auto-refreshes via WebSocket telemetry events.
 * Sparkline mini-charts show rolling metric history.
 */

import { esc, fetchJSON, formatDuration, formatNumber, el } from '../theme.js';
import { ws } from '../ws.js';
import { showToast } from '../components/toast.js';
import { drawSparkline } from '../components/sparkline.js';

let containerEl = null;
let refreshTimer = null;
let unsubTelemetry = null;

// Cached data
let data = {
  sessions: { count: 0, sessions: [] },
  memory: { enabled: false, count: 0, entries: [] },
  telemetry: { enabled: false, summary: {}, metrics: [] },
  scheduler: { jobs: [] },
  config: {},
};

// Count enabled capability/runtime features for the overview card.
function _capsCount() {
  const c = data.config || {};
  const cap = c.capabilities || {};
  const flags = [
    cap.scraper && cap.scraper.enabled, cap.github && cap.github.enabled,
    cap.jsonrpc && cap.jsonrpc.enabled, cap.notify && cap.notify.enabled,
    cap.computer && cap.computer.enabled,
    c.macos && c.macos.enabled, c.lsp && c.lsp.enabled,
    c.runtime_tools && c.runtime_tools.enabled,
    c.session_recorder && c.session_recorder.enabled,
    c.ambient && c.ambient.enabled, c.mcp && c.mcp.enabled,
  ];
  return { on: flags.filter(Boolean).length, total: flags.length };
}

// Sparkline history — rolling window of last 20 snapshots
const SPARK_MAX = 20;
const sparkHistory = {
  sessions: [],
  memory: [],
  tools: [],
  model: [],
  errors: [],
  jobs: [],
};

export function mount(container) {
  containerEl = container;
  _render();
  _fetchAll();

  // Subscribe to telemetry events for live updates
  unsubTelemetry = ws.subscribe('telemetry', () => {
    _fetchTelemetry();
  });

  // Periodic refresh for non-WS data (every 10s)
  refreshTimer = setInterval(_fetchAll, 10000);
}

export function unmount() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (unsubTelemetry) {
    unsubTelemetry();
    unsubTelemetry = null;
  }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  const s = data.telemetry.summary || {};
  const toolCalls = s.total_tool_calls || 0;
  const modelCalls = s.total_model_calls || 0;
  const errors = s.error_count || 0;
  const avgTool = s.avg_tool_duration || 0;
  const avgModel = s.avg_model_duration || 0;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2302</span>
        Dashboard Overview
      </h2>
    </div>

    <!-- Summary Cards -->
    <div class="summary-grid" id="summary-cards">
      <div class="summary-card">
        <div class="card-icon">\u25C9</div>
        <div class="card-value text-mono" id="card-sessions">${data.sessions.count}</div>
        <div class="card-label">Active Sessions</div>
        <div class="card-sub">${_sessionSub()}</div>
        <div class="card-sparkline"><canvas id="spark-sessions"></canvas></div>
      </div>
      <div class="summary-card">
        <div class="card-icon">\u29BF</div>
        <div class="card-value text-mono" id="card-memory">${data.memory.enabled ? formatNumber(data.memory.count) : '--'}</div>
        <div class="card-label">Memory Entries</div>
        <div class="card-sub">${data.memory.enabled ? 'Vector memory active' : 'Memory disabled'}</div>
        <div class="card-sparkline"><canvas id="spark-memory"></canvas></div>
      </div>
      <div class="summary-card">
        <div class="card-icon">\u2699</div>
        <div class="card-value text-mono" id="card-tools">${formatNumber(toolCalls)}</div>
        <div class="card-label">Tool Calls</div>
        <div class="card-sub">Avg: ${formatDuration(avgTool)}</div>
        <div class="card-sparkline"><canvas id="spark-tools"></canvas></div>
      </div>
      <div class="summary-card">
        <div class="card-icon">\u2726</div>
        <div class="card-value text-mono" id="card-model">${formatNumber(modelCalls)}</div>
        <div class="card-label">Model Calls</div>
        <div class="card-sub">Avg: ${formatDuration(avgModel)}</div>
        <div class="card-sparkline"><canvas id="spark-model"></canvas></div>
      </div>
      <div class="summary-card">
        <div class="card-icon">${errors > 0 ? '\u2716' : '\u2714'}</div>
        <div class="card-value text-mono" id="card-errors" style="color:${errors > 0 ? 'var(--color-error)' : 'var(--color-success)'}">${errors}</div>
        <div class="card-label">Errors</div>
        <div class="card-sub">${errors > 0 ? 'Check logs for details' : 'All systems normal'}</div>
        <div class="card-sparkline"><canvas id="spark-errors"></canvas></div>
      </div>
      <div class="summary-card">
        <div class="card-icon">\u23F0</div>
        <div class="card-value text-mono" id="card-jobs">${data.scheduler.jobs.length}</div>
        <div class="card-label">Scheduled Jobs</div>
        <div class="card-sub">${_jobsSub()}</div>
        <div class="card-sparkline"><canvas id="spark-jobs"></canvas></div>
      </div>
      <a class="summary-card" href="#/features" style="text-decoration:none;color:inherit">
        <div class="card-icon">\u26A1</div>
        <div class="card-value text-mono" id="card-caps">${_capsCount().on}<span style="color:var(--text-muted);font-size:0.6em">/${_capsCount().total}</span></div>
        <div class="card-label">Capabilities</div>
        <div class="card-sub">Enabled features \u2192 open Features</div>
        <div class="card-sparkline"></div>
      </a>
    </div>

    <!-- Recent Activity -->
    <div class="glass-card mt-md">
      <div class="glass-card-header">
        <span class="glass-card-title">\u2261 Recent Telemetry</span>
        <span class="glass-card-badge">${data.telemetry.metrics.length} events</span>
      </div>
      <div id="recent-metrics" style="max-height:300px;overflow-y:auto">
        ${_renderMetrics()}
      </div>
    </div>
  `;

  // Draw sparklines after DOM is ready
  _drawSparklines();
}

function _sessionSub() {
  if (data.sessions.count === 0) return 'No active sessions';
  const names = data.sessions.sessions.slice(0, 3).map(s => s.agent_name || 'AETHON');
  return names.join(', ') + (data.sessions.count > 3 ? ` +${data.sessions.count - 3} more` : '');
}

function _jobsSub() {
  if (data.scheduler.jobs.length === 0) return 'No scheduled jobs';
  return data.scheduler.jobs.slice(0, 2).map(j => j.job_id || j.sop_name || 'job').join(', ');
}

function _renderMetrics() {
  const metrics = data.telemetry.metrics || [];
  if (metrics.length === 0) {
    return '<div class="empty-state"><div class="empty-text">No telemetry data yet</div></div>';
  }

  return metrics.slice(0, 20).map(m => {
    const type = m.type || '?';
    const name = m.name || '-';
    const duration = m.duration ? formatDuration(m.duration) : '-';
    const status = m.status || '-';
    const isError = status === 'error';

    return `<div class="log-entry">
      <span class="log-level ${isError ? 'log-level-error' : 'log-level-info'}">${esc(type)}</span>
      <span class="log-module">${esc(name)}</span>
      <span class="log-msg text-mono">${duration}</span>
      <span class="badge ${isError ? 'badge-red' : 'badge-green'}">${esc(status)}</span>
    </div>`;
  }).join('');
}

async function _fetchAll() {
  await Promise.allSettled([
    _fetchSessions(),
    _fetchMemory(),
    _fetchTelemetry(),
    _fetchJobs(),
    _fetchConfig(),
  ]);
  _pushSparkData();
  _render();
}

async function _fetchConfig() {
  try {
    data.config = await fetchJSON('/api/config');
  } catch (e) {
    console.error('[Overview] Failed to fetch config:', e);
  }
}

async function _fetchSessions() {
  try {
    data.sessions = await fetchJSON('/api/sessions');
  } catch (e) {
    console.error('[Overview] Failed to fetch sessions:', e);
  }
}

async function _fetchMemory() {
  try {
    data.memory = await fetchJSON('/api/memory');
  } catch (e) {
    console.error('[Overview] Failed to fetch memory:', e);
  }
}

async function _fetchTelemetry() {
  try {
    data.telemetry = await fetchJSON('/api/telemetry');
    if (containerEl) {
      _pushSparkData();
      _updateTelemetryCards();
      _drawSparklines();
    }
  } catch (e) {
    console.error('[Overview] Failed to fetch telemetry:', e);
  }
}

async function _fetchJobs() {
  try {
    data.scheduler = await fetchJSON('/api/scheduler/jobs');
  } catch (e) {
    console.error('[Overview] Failed to fetch jobs:', e);
  }
}

/** Push current metric values into sparkline history buffers. */
function _pushSparkData() {
  const s = data.telemetry.summary || {};

  _pushVal(sparkHistory.sessions, data.sessions.count || 0);
  _pushVal(sparkHistory.memory, data.memory.count || 0);
  _pushVal(sparkHistory.tools, s.total_tool_calls || 0);
  _pushVal(sparkHistory.model, s.total_model_calls || 0);
  _pushVal(sparkHistory.errors, s.error_count || 0);
  _pushVal(sparkHistory.jobs, (data.scheduler.jobs || []).length);
}

function _pushVal(arr, val) {
  arr.push(val);
  if (arr.length > SPARK_MAX) arr.shift();
}

/** Draw all sparkline canvases. */
function _drawSparklines() {
  if (!containerEl) return;

  const sparkConfigs = [
    { id: 'spark-sessions', data: sparkHistory.sessions, color: '#00d4ff' },
    { id: 'spark-memory',   data: sparkHistory.memory,   color: '#00ff88' },
    { id: 'spark-tools',    data: sparkHistory.tools,    color: '#00d4ff' },
    { id: 'spark-model',    data: sparkHistory.model,    color: '#ffbd2e' },
    { id: 'spark-errors',   data: sparkHistory.errors,   color: '#ff5f57' },
    { id: 'spark-jobs',     data: sparkHistory.jobs,     color: '#ff00ff' },
  ];

  for (const cfg of sparkConfigs) {
    const canvas = document.getElementById(cfg.id);
    if (!canvas) continue;

    // Need at least 2 data points for a line
    if (cfg.data.length < 2) {
      // Draw a flat line with current value
      const flat = cfg.data.length === 1 ? [cfg.data[0], cfg.data[0]] : [0, 0];
      drawSparkline(canvas, flat, { color: cfg.color, fillOpacity: 0.08, showDot: false });
    } else {
      drawSparkline(canvas, cfg.data, { color: cfg.color });
    }
  }
}

function _updateTelemetryCards() {
  const s = data.telemetry.summary || {};
  _updateCard('card-tools', formatNumber(s.total_tool_calls || 0));
  _updateCard('card-model', formatNumber(s.total_model_calls || 0));
  _updateCard('card-errors', s.error_count || 0);

  const metricsEl = document.getElementById('recent-metrics');
  if (metricsEl) {
    metricsEl.innerHTML = _renderMetrics();
  }
}

function _updateCard(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}
