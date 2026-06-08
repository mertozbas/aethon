/**
 * AETHON Dashboard — Live Company Panel
 *
 * Full-screen pixel art office showing real agents as characters.
 * Subscribes to 'agents' and 'telemetry' WS channels for real-time updates.
 * Fetches initial agent list from /api/agents/active.
 */

import { fetchJSON } from '../theme.js';
import { ws } from '../ws.js';
import { PixelOfficeEngine } from '../pixel-office/engine.js';

let containerEl = null;
let engine = null;
let unsubAgents = null;
let unsubTelemetry = null;
let refreshTimer = null;

export function mount(container) {
  containerEl = container;
  _render();

  // Initialize pixel office engine
  const canvas = container.querySelector('#pixel-office-canvas');
  if (canvas) {
    try {
      engine = new PixelOfficeEngine(canvas);
      engine.start();
      console.log('[Company] Pixel office engine started');

      // Fetch initial agents
      _fetchAgents();

      // Real-time activity — the 'agents' channel now carries session identity
      // (tool_start / tool_end / model), so each event maps to the right
      // character. (Previously telemetry was also routed here, but it lacked a
      // session id and spawned a phantom "unknown" character.)
      unsubAgents = ws.subscribe('agents', (data) => {
        if (engine) engine.onAgentEvent(data);
      });

      // Periodic sync
      refreshTimer = setInterval(_fetchAgents, 15000);
    } catch (e) {
      console.error('[Company] Failed to start pixel office:', e);
      _showError(container, e.message);
    }
  }
}

export function unmount() {
  if (engine) {
    engine.stop();
    engine = null;
  }
  if (unsubAgents) { unsubAgents(); unsubAgents = null; }
  if (unsubTelemetry) { unsubTelemetry(); unsubTelemetry = null; }
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="company-panel">
      <div class="company-header">
        <div class="company-title">
          <span class="title-icon">\u{1F3E2}</span>
          <span>AETHON HQ</span>
          <span class="company-subtitle">Live Agent Activity</span>
        </div>
        <div class="company-controls">
          <span class="text-mono text-sm text-muted" id="company-agent-count">0 agents</span>
          <button class="btn btn-sm btn-ghost" id="company-zoom-out" aria-label="Zoom out">\u2796</button>
          <span class="text-mono text-sm" id="company-zoom-level">2x</span>
          <button class="btn btn-sm btn-ghost" id="company-zoom-in" aria-label="Zoom in">\u2795</button>
          <button class="btn btn-sm btn-ghost" id="company-refresh" aria-label="Refresh">\u21BB</button>
        </div>
      </div>
      <div class="company-canvas-wrapper" id="company-canvas-wrapper">
        <canvas id="pixel-office-canvas"></canvas>
      </div>
      <div class="company-legend">
        <div class="legend-item">
          <span class="legend-dot" style="background:#3498DB"></span>
          <span>Coder</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:#E74C3C"></span>
          <span>Researcher</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:#27AE60"></span>
          <span>Analyst</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:#9B59B6"></span>
          <span>Planner</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:#E67E22"></span>
          <span>Builder</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" style="background:#1ABC9C"></span>
          <span>Creative</span>
        </div>
        <span class="text-sm text-muted" style="margin-left:auto">
          \u{1F4BB} typing = working \u00A0\u00A0 \u{1F4D6} reading = searching \u00A0\u00A0 \u{1F6B6} walking = idle
        </span>
      </div>
    </div>
  `;

  // Zoom controls
  const zoomIn = containerEl.querySelector('#company-zoom-in');
  const zoomOut = containerEl.querySelector('#company-zoom-out');
  const zoomLabel = containerEl.querySelector('#company-zoom-level');

  if (zoomIn) zoomIn.addEventListener('click', () => {
    if (engine) {
      engine.setZoom(engine.zoom + 1);
      if (zoomLabel) zoomLabel.textContent = engine.zoom + 'x';
    }
  });

  if (zoomOut) zoomOut.addEventListener('click', () => {
    if (engine) {
      engine.setZoom(engine.zoom - 1);
      if (zoomLabel) zoomLabel.textContent = engine.zoom + 'x';
    }
  });

  // Refresh
  const refreshBtn = containerEl.querySelector('#company-refresh');
  if (refreshBtn) refreshBtn.addEventListener('click', _fetchAgents);
}

async function _fetchAgents() {
  try {
    const data = await fetchJSON('/api/agents/active');
    const agents = data.agents || [];

    const countEl = containerEl ? containerEl.querySelector('#company-agent-count') : null;
    if (countEl) countEl.textContent = `${agents.length} agent${agents.length !== 1 ? 's' : ''}`;

    if (engine) {
      engine.syncAgents(agents);
    }
  } catch (e) {
    console.error('[Company] Fetch agents error:', e);
  }
}

function _showError(container, msg) {
  const wrapper = container.querySelector('#company-canvas-wrapper');
  if (wrapper) {
    wrapper.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u26A0</div>
        <div class="empty-text">Failed to initialize Pixel Office</div>
        <div class="empty-sub">${msg || 'Unknown error'}</div>
      </div>
    `;
  }
}
