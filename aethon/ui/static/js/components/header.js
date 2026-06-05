/**
 * AETHON Dashboard — Header Component
 *
 * Top bar with page title, connection status indicator,
 * and reconnection banner.
 */

import { ws } from '../ws.js';

let headerEl = null;
let dotEl = null;
let statusTextEl = null;

/**
 * Initialize the header.
 * @param {HTMLElement} container — The #header element
 */
export function init(container) {
  headerEl = container;

  headerEl.innerHTML = `
    <div class="reconnect-banner hidden" id="reconnect-banner" role="alert">
      \u26A0 WebSocket disconnected \u2014 reconnecting...
    </div>
    <div class="header-left">
      <span class="header-title" id="header-panel-title">Overview</span>
    </div>
    <div class="header-right">
      <div class="connection-status" aria-label="WebSocket connection status">
        <span class="connection-dot" id="ws-dot"></span>
        <span id="ws-status-text" class="text-mono">Disconnected</span>
      </div>
    </div>
  `;

  dotEl = headerEl.querySelector('#ws-dot');
  statusTextEl = headerEl.querySelector('#ws-status-text');

  // Listen for WS state changes (supports multiple listeners)
  ws.onStateChange(_updateConnectionStatus);

  // Set initial state
  _updateConnectionStatus(ws.state);
}

/**
 * Update the panel title displayed in the header.
 * @param {string} title
 */
export function setTitle(title) {
  const titleEl = document.getElementById('header-panel-title');
  if (titleEl) {
    titleEl.textContent = title;
  }
}

// --- Private ---

const TITLE_MAP = {
  '/overview': 'Overview',
  '/company': 'Live Company',
  '/monitor': 'Live Monitor',
  '/sessions': 'Sessions',
  '/memory': 'Memory Explorer',
  '/config': 'Configuration',
  '/logs': 'Log Viewer',
  '/agents': 'Agent Activity',
  '/sops': 'SOP Editor',
};

/**
 * Update title based on route path.
 * @param {string} path
 */
export function updateTitleFromRoute(path) {
  setTitle(TITLE_MAP[path] || 'AETHON');
}

let _hadConnection = false;

function _updateConnectionStatus(state) {
  if (!dotEl || !statusTextEl) return;

  dotEl.classList.remove('connected', 'connecting');
  const banner = document.getElementById('reconnect-banner');

  switch (state) {
    case 'connected':
      dotEl.classList.add('connected');
      statusTextEl.textContent = 'Connected';
      if (banner) banner.classList.add('hidden');
      _hadConnection = true;
      break;
    case 'connecting':
      dotEl.classList.add('connecting');
      statusTextEl.textContent = 'Connecting...';
      break;
    default:
      statusTextEl.textContent = 'Disconnected';
      if (banner && _hadConnection) banner.classList.remove('hidden');
      break;
  }
}
