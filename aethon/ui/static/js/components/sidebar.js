/**
 * AETHON Dashboard — Sidebar Navigation Component
 *
 * Icon-based navigation with active highlight, collapsible on mobile.
 * Uses Unicode symbols for icons — zero image dependencies.
 */

import * as router from '../router.js';

const NAV_ITEMS = [
  { path: '/overview', icon: '\u2302', label: 'Overview' },
  { path: '/company',  icon: '\u{1F3E2}', label: 'Live Company' },
  { path: '/monitor',  icon: '\u25C9', label: 'Live Monitor' },
  { path: '/sessions', icon: '\u2630', label: 'Sessions' },
  { path: '/memory',   icon: '\u29BF', label: 'Memory' },
  { path: '/config',   icon: '\u2699', label: 'Config' },
  { path: '/logs',     icon: '\u2261', label: 'Logs' },
  { path: '/agents',   icon: '\u2726', label: 'Agents' },
  { path: '/sops',     icon: '\u2637', label: 'SOPs' },
];

let sidebarEl = null;
let toggleBtn = null;

/**
 * Initialize the sidebar.
 * @param {HTMLElement} container — The #sidebar element
 */
export function init(container) {
  sidebarEl = container;
  render();
  _createMobileToggle();
}

/**
 * Update active state when route changes.
 * @param {string} path
 */
export function setActive(path) {
  if (!sidebarEl) return;
  const items = sidebarEl.querySelectorAll('.nav-item');
  items.forEach(item => {
    const itemPath = item.getAttribute('data-path');
    if (itemPath === path) {
      item.classList.add('active');
      item.setAttribute('aria-current', 'page');
    } else {
      item.classList.remove('active');
      item.removeAttribute('aria-current');
    }
  });

  // Close mobile sidebar after navigation
  if (sidebarEl.classList.contains('open')) {
    sidebarEl.classList.remove('open');
  }
}

function render() {
  const currentPath = router.current();

  sidebarEl.innerHTML = `
    <div class="sidebar-logo">
      <div class="logo-icon" aria-hidden="true">A</div>
      <span class="logo-text">AETHON</span>
    </div>
    <div class="sidebar-nav" role="list">
      ${NAV_ITEMS.map(item => `
        <a class="nav-item${item.path === currentPath ? ' active' : ''}"
           data-path="${item.path}"
           href="#${item.path}"
           role="listitem"
           ${item.path === currentPath ? 'aria-current="page"' : ''}
           aria-label="${item.label}">
          <span class="nav-icon" aria-hidden="true">${item.icon}</span>
          <span class="nav-label">${item.label}</span>
        </a>
      `).join('')}
    </div>
    <div class="sidebar-footer">
      AETHON v1.0
    </div>
  `;

  // Click handlers (event delegation)
  sidebarEl.addEventListener('click', (e) => {
    const navItem = e.target.closest('.nav-item');
    if (navItem) {
      // Hash navigation happens via href, but we prevent default for SPA
      // Actually href="#/path" will trigger hashchange, so let it work naturally
    }
  });
}

function _createMobileToggle() {
  // Create hamburger toggle button for mobile
  toggleBtn = document.createElement('button');
  toggleBtn.className = 'sidebar-toggle';
  toggleBtn.innerHTML = '\u2630';
  toggleBtn.setAttribute('aria-label', 'Toggle navigation');
  toggleBtn.addEventListener('click', () => {
    if (sidebarEl) {
      sidebarEl.classList.toggle('open');
    }
  });
  document.body.appendChild(toggleBtn);

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (sidebarEl && sidebarEl.classList.contains('open') &&
        !sidebarEl.contains(e.target) && e.target !== toggleBtn) {
      sidebarEl.classList.remove('open');
    }
  });
}
