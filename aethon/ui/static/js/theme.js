/**
 * AETHON Dashboard — Shared Utilities & Theme
 *
 * HTML escaping, time formatting, fetch helpers, theme management.
 */

/**
 * Escape HTML entities to prevent XSS.
 * @param {*} s
 * @returns {string}
 */
export function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Format a timestamp for display.
 * @param {string|number|Date} ts — ISO string, unix ms, or Date
 * @returns {string} — e.g. "14:23:05"
 */
export function formatTime(ts) {
  try {
    const d = ts instanceof Date ? ts : new Date(ts);
    if (isNaN(d.getTime())) return '--:--:--';
    return d.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return '--:--:--';
  }
}

/**
 * Format a timestamp as date + time.
 * @param {string|number|Date} ts
 * @returns {string} — e.g. "2026-03-13 14:23"
 */
export function formatDateTime(ts) {
  try {
    const d = ts instanceof Date ? ts : new Date(ts);
    if (isNaN(d.getTime())) return '--';
    const date = d.toISOString().slice(0, 10);
    const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    return `${date} ${time}`;
  } catch {
    return '--';
  }
}

/**
 * Format a duration in seconds to human-readable.
 * @param {number} seconds
 * @returns {string} — e.g. "1.23s", "5m 12s", "2h 3m"
 */
export function formatDuration(seconds) {
  if (typeof seconds !== 'number' || isNaN(seconds)) return '--';
  if (seconds < 0.001) return '0ms';
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m < 60) return `${m}m ${s}s`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `${h}h ${rm}m`;
}

/**
 * Format a number with K/M/B suffixes.
 * @param {number} n
 * @returns {string}
 */
export function formatNumber(n) {
  if (typeof n !== 'number' || isNaN(n)) return '0';
  if (n < 1000) return n.toString();
  if (n < 1_000_000) return (n / 1000).toFixed(1) + 'K';
  if (n < 1_000_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  return (n / 1_000_000_000).toFixed(1) + 'B';
}

/**
 * Fetch JSON from an API endpoint.
 * @param {string} url
 * @param {Object} [options]
 * @returns {Promise<Object>}
 */
export async function fetchJSON(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }
  return resp.json();
}

/**
 * POST JSON to an API endpoint.
 * @param {string} url
 * @param {Object} body
 * @returns {Promise<Object>}
 */
export async function postJSON(url, body) {
  return fetchJSON(url, {
    method: 'POST',
    body: JSON.stringify(body)
  });
}

/**
 * Debounce a function.
 * @param {Function} fn
 * @param {number} ms
 * @returns {Function}
 */
export function debounce(fn, ms) {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn.apply(this, args);
    }, ms);
  };
}

/**
 * Create an HTML element with optional attributes and children.
 * @param {string} tag
 * @param {Object} [attrs]
 * @param {(string|HTMLElement)[]} [children]
 * @returns {HTMLElement}
 */
export function el(tag, attrs = {}, children = []) {
  const elem = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === 'className') {
      elem.className = val;
    } else if (key === 'style' && typeof val === 'object') {
      Object.assign(elem.style, val);
    } else if (key.startsWith('on') && typeof val === 'function') {
      elem.addEventListener(key.slice(2).toLowerCase(), val);
    } else if (key === 'innerHTML') {
      elem.innerHTML = val;
    } else {
      elem.setAttribute(key, val);
    }
  }
  for (const child of children) {
    if (typeof child === 'string') {
      elem.appendChild(document.createTextNode(child));
    } else if (child instanceof HTMLElement) {
      elem.appendChild(child);
    }
  }
  return elem;
}

// --- Theme Presets ---

const THEMES = {
  cyberpunk: {
    '--accent-primary': '#00d4ff',
    '--accent-secondary': '#00ff88',
    '--accent-tertiary': '#ff00ff',
  },
  neon_green: {
    '--accent-primary': '#00ff88',
    '--accent-secondary': '#00d4ff',
    '--accent-tertiary': '#ff00ff',
  },
  ocean_blue: {
    '--accent-primary': '#4488ff',
    '--accent-secondary': '#00d4ff',
    '--accent-tertiary': '#aa44ff',
  },
  magenta: {
    '--accent-primary': '#ff00ff',
    '--accent-secondary': '#ff5f57',
    '--accent-tertiary': '#00d4ff',
  },
};

/**
 * Apply a theme preset.
 * @param {string} name
 */
export function setTheme(name) {
  const vars = THEMES[name];
  if (!vars) return;
  const root = document.documentElement;
  for (const [prop, val] of Object.entries(vars)) {
    root.style.setProperty(prop, val);
  }
  localStorage.setItem('aethon-theme', JSON.stringify(vars));
  localStorage.setItem('aethon-theme-name', name);
}

/**
 * Get current theme name.
 * @returns {string}
 */
export function getThemeName() {
  return localStorage.getItem('aethon-theme-name') || 'cyberpunk';
}

/**
 * Get available theme names.
 * @returns {string[]}
 */
export function getThemeNames() {
  return Object.keys(THEMES);
}
