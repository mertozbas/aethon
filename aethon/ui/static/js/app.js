/**
 * AETHON Dashboard — Application Entry Point
 *
 * Initializes: WebSocket, Router, Sidebar, Header, Toast, Modal.
 * Registers all panel modules and starts the SPA.
 */

import { ws } from './ws.js';
import * as router from './router.js';
import * as sidebar from './components/sidebar.js';
import * as header from './components/header.js';
import * as toast from './components/toast.js';
import * as modal from './components/modal.js';

// Panels
import * as overview from './panels/overview.js';
import * as monitor from './panels/monitor.js';
import * as logs from './panels/logs.js';
import * as sessions from './panels/sessions.js';
import * as recordings from './panels/recordings.js';
import * as memory from './panels/memory.js';
import * as configPanel from './panels/config.js';
import * as features from './panels/features.js';
import * as sops from './panels/sops.js';
import * as agents from './panels/agents.js';
import * as company from './panels/company.js';

async function boot() {
  console.log('[AETHON] Dashboard booting...');

  // 1. Initialize components
  const sidebarEl = document.getElementById('sidebar');
  const headerEl = document.getElementById('header');
  const contentEl = document.getElementById('content');
  const toastEl = document.getElementById('toast-container');
  const modalEl = document.getElementById('modal-overlay');

  sidebar.init(sidebarEl);
  header.init(headerEl);
  toast.init(toastEl);
  modal.init(modalEl);

  // 2. Register panel routes
  router.register('/overview', overview);

  router.register('/monitor', monitor);
  router.register('/sessions', sessions);
  router.register('/recordings', recordings);
  router.register('/memory', memory);
  router.register('/config', configPanel);
  router.register('/features', features);
  router.register('/logs', logs);
  router.register('/agents', agents);
  router.register('/sops', sops);
  router.register('/company', company);

  // 3. Initialize router with route change callback
  router.init(contentEl, (path) => {
    sidebar.setActive(path);
    header.updateTitleFromRoute(path);
  });

  // Set initial active state
  sidebar.setActive(router.current());
  header.updateTitleFromRoute(router.current());

  // 4. Connect WebSocket
  ws.connect();

  // Show connection toast (header also listens — multiple callbacks supported)
  let hadConnection = false;
  ws.onStateChange((state) => {
    if (state === 'connected') {
      toast.success('WebSocket connected');
      hadConnection = true;
    } else if (state === 'disconnected' && hadConnection) {
      toast.warning('WebSocket disconnected — reconnecting...');
    }
  });

  console.log('[AETHON] Dashboard ready.');
}

// Boot on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
