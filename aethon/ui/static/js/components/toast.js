/**
 * AETHON Dashboard — Toast Notification System
 *
 * Floating notifications with auto-dismiss and type-based styling.
 * Types: success, error, warning, info
 */

const ICONS = {
  success: '\u2714',   // checkmark
  error: '\u2716',     // cross
  warning: '\u26A0',   // warning sign
  info: '\u2139',      // info
};

const DEFAULT_DURATION = 4000;
const MAX_TOASTS = 5;

let containerEl = null;

/**
 * Initialize the toast system.
 * @param {HTMLElement} [container] — The #toast-container element
 */
export function init(container) {
  containerEl = container || document.getElementById('toast-container');
}

/**
 * Show a toast notification.
 * @param {string} message
 * @param {string} [type='info'] — success | error | warning | info
 * @param {number} [duration=4000] — Auto-dismiss time in ms (0 = no auto-dismiss)
 */
export function showToast(message, type = 'info', duration = DEFAULT_DURATION) {
  if (!containerEl) {
    containerEl = document.getElementById('toast-container');
  }
  if (!containerEl) return;

  // Enforce max toasts
  while (containerEl.children.length >= MAX_TOASTS) {
    containerEl.removeChild(containerEl.lastChild);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast-icon" aria-hidden="true">${ICONS[type] || ICONS.info}</span>
    <span class="toast-msg">${message}</span>
  `;

  containerEl.insertBefore(toast, containerEl.firstChild);

  if (duration > 0) {
    setTimeout(() => _dismiss(toast), duration);
  }

  // Click to dismiss
  toast.addEventListener('click', () => _dismiss(toast));

  return toast;
}

function _dismiss(toast) {
  if (!toast || !toast.parentNode) return;
  toast.classList.add('toast-out');
  toast.addEventListener('animationend', () => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  });
}

// Convenience methods
export const success = (msg, dur) => showToast(msg, 'success', dur);
export const error = (msg, dur) => showToast(msg, 'error', dur);
export const warning = (msg, dur) => showToast(msg, 'warning', dur);
export const info = (msg, dur) => showToast(msg, 'info', dur);
