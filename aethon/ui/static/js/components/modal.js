/**
 * AETHON Dashboard — Modal Dialog Component
 *
 * Confirmation dialogs with glassmorphism styling.
 * Supports keyboard (Escape to close, Enter to confirm).
 */

let overlayEl = null;

/**
 * Initialize the modal system.
 * @param {HTMLElement} [overlay] — The #modal-overlay element
 */
export function init(overlay) {
  overlayEl = overlay || document.getElementById('modal-overlay');

  // Close on overlay click (outside modal box)
  if (overlayEl) {
    overlayEl.addEventListener('click', (e) => {
      if (e.target === overlayEl) {
        hide();
      }
    });
  }

  // Escape key to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlayEl && !overlayEl.classList.contains('hidden')) {
      hide();
    }
  });
}

/**
 * Show a confirmation modal.
 * @param {string} title
 * @param {string} body — Can contain HTML
 * @param {Function} onConfirm — Called when user clicks Confirm
 * @param {Object} [options]
 * @param {string} [options.confirmText='Confirm']
 * @param {string} [options.cancelText='Cancel']
 * @param {string} [options.confirmClass='btn-primary'] — CSS class for confirm button
 */
export function showModal(title, body, onConfirm, options = {}) {
  if (!overlayEl) {
    overlayEl = document.getElementById('modal-overlay');
  }
  if (!overlayEl) return;

  const confirmText = options.confirmText || 'Confirm';
  const cancelText = options.cancelText || 'Cancel';
  const confirmClass = options.confirmClass || 'btn-primary';

  overlayEl.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${title}</div>
      <div class="modal-body">${body}</div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="modal-cancel" aria-label="${cancelText}">${cancelText}</button>
        <button class="btn ${confirmClass}" id="modal-confirm" aria-label="${confirmText}">${confirmText}</button>
      </div>
    </div>
  `;

  overlayEl.classList.remove('hidden');

  // Focus the confirm button
  const confirmBtn = overlayEl.querySelector('#modal-confirm');
  const cancelBtn = overlayEl.querySelector('#modal-cancel');

  if (confirmBtn) {
    confirmBtn.focus();
    confirmBtn.addEventListener('click', () => {
      hide();
      if (onConfirm) onConfirm();
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', hide);
  }

  // Enter key to confirm
  const keyHandler = (e) => {
    if (e.key === 'Enter') {
      hide();
      document.removeEventListener('keydown', keyHandler);
      if (onConfirm) onConfirm();
    }
  };
  document.addEventListener('keydown', keyHandler);
}

/**
 * Hide the modal.
 */
export function hide() {
  if (overlayEl) {
    overlayEl.classList.add('hidden');
    overlayEl.innerHTML = '';
  }
}

/**
 * Check if modal is currently visible.
 * @returns {boolean}
 */
export function isVisible() {
  return overlayEl ? !overlayEl.classList.contains('hidden') : false;
}
