/**
 * AETHON Dashboard — Hash-based SPA Router
 *
 * Routes:
 *   #/overview  — Home panel (default)
 *   #/monitor   — Live chat monitor
 *   #/sessions  — Session browser
 *   #/memory    — Memory explorer
 *   #/config    — Config editor
 *   #/logs      — Log viewer
 *   #/agents    — Agent activity
 *   #/sops      — SOP editor
 *
 * Each panel module exports: { mount(container), unmount() }
 */

/** @type {Map<string, {mount: Function, unmount: Function}>} */
const routes = new Map();

/** @type {string|null} */
let currentRoute = null;

/** @type {HTMLElement|null} */
let contentEl = null;

/** @type {Function|null} */
let onRouteChange = null;

/**
 * Register a panel module for a route.
 * @param {string} path — e.g. '/overview'
 * @param {{mount: Function, unmount: Function}} panel
 */
export function register(path, panel) {
  routes.set(path, panel);
}

/**
 * Initialize the router.
 * @param {HTMLElement} container — The #content element
 * @param {Function} [onChange] — Called with (path) after route change
 */
export function init(container, onChange) {
  contentEl = container;
  onRouteChange = onChange || null;

  window.addEventListener('hashchange', _handleRoute);

  // Navigate to current hash or default
  _handleRoute();
}

/**
 * Navigate programmatically.
 * @param {string} path — e.g. '/overview'
 */
export function navigate(path) {
  window.location.hash = '#' + path;
}

/**
 * Get current route path.
 * @returns {string}
 */
export function current() {
  return currentRoute || '/overview';
}

// --- Private ---

function _handleRoute() {
  const hash = window.location.hash || '#/overview';
  const path = hash.slice(1); // Remove '#'

  // Don't re-mount same panel
  if (path === currentRoute) return;

  // Unmount current panel
  if (currentRoute) {
    const prev = routes.get(currentRoute);
    if (prev && prev.unmount) {
      try {
        prev.unmount();
      } catch (e) {
        console.error(`[Router] Error unmounting "${currentRoute}":`, e);
      }
    }
  }

  // Find panel for new route
  let panel = routes.get(path);

  // Fallback to /overview if route not found
  if (!panel) {
    panel = routes.get('/overview');
    if (panel && path !== '/overview') {
      // Redirect to overview
      window.location.hash = '#/overview';
      return;
    }
  }

  currentRoute = path;

  // Clear content
  if (contentEl) {
    contentEl.innerHTML = '';
  }

  // Mount new panel
  if (panel && panel.mount && contentEl) {
    try {
      panel.mount(contentEl);
    } catch (e) {
      console.error(`[Router] Error mounting "${path}":`, e);
      if (contentEl) {
        contentEl.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">&#x26A0;</div>
            <div class="empty-text">Error loading panel</div>
            <div class="empty-sub">${path}</div>
          </div>
        `;
      }
    }
  }

  // Notify listeners
  if (onRouteChange) {
    onRouteChange(path);
  }
}
