/**
 * AETHON Dashboard — SOP Editor Panel
 *
 * List, view, edit, and create Standard Operating Procedures.
 * Built-in SOPs are read-only. Custom SOPs can be edited and saved.
 */

import { esc, fetchJSON } from '../theme.js';
import { showToast } from '../components/toast.js';
import { showModal } from '../components/modal.js';

let containerEl = null;
let sops = [];
let selectedSop = null;
let sopContent = '';
let isEditing = false;

export function mount(container) {
  containerEl = container;
  sops = [];
  selectedSop = null;
  sopContent = '';
  isEditing = false;
  _render();
  _fetchSops();
}

export function unmount() {
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u{1F4CB}</span>
        SOP Editor
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="sop-count">-</span>
        <button class="btn btn-sm btn-primary" id="sop-new-btn" aria-label="New SOP">\u2795 New</button>
        <button class="btn btn-sm btn-ghost" id="sop-refresh" aria-label="Refresh">\u21BB</button>
      </div>
    </div>

    <!-- SOP layout: list + editor -->
    <div class="session-layout" id="sop-layout">
      <!-- SOP list -->
      <div class="glass-card" style="padding:0;overflow-y:auto;max-height:calc(100vh - 240px)">
        <div id="sop-list">
          <div class="empty-state">
            <div class="empty-icon">\u{1F4CB}</div>
            <div class="empty-text">Loading SOPs...</div>
          </div>
        </div>
      </div>

      <!-- SOP editor -->
      <div id="sop-editor" style="display:none">
        <div class="glass-card" style="padding:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <h3 style="margin:0;color:var(--accent-primary)" id="sop-editor-title">SOP</h3>
            <div style="display:flex;gap:8px" id="sop-editor-actions"></div>
          </div>
          <div id="sop-editor-content"></div>
        </div>
      </div>
    </div>
  `;

  // Event listeners
  containerEl.querySelector('#sop-refresh').addEventListener('click', _fetchSops);

  containerEl.querySelector('#sop-new-btn').addEventListener('click', () => {
    _startNewSop();
  });
}

async function _fetchSops() {
  try {
    const data = await fetchJSON('/api/sops');
    sops = data.sops || [];
    const countEl = containerEl ? containerEl.querySelector('#sop-count') : null;
    if (countEl) countEl.textContent = `${sops.length} SOPs`;
    _renderSopList();

    if (!data.enabled) {
      const listEl = containerEl ? containerEl.querySelector('#sop-list') : null;
      if (listEl) {
        listEl.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">\u26A0</div>
            <div class="empty-text">SOPs not enabled</div>
            <div class="empty-sub">Enable SOPs in aethon.yaml configuration</div>
          </div>
        `;
      }
    }
  } catch (e) {
    console.error('[SOPs] Fetch error:', e);
  }
}

function _renderSopList() {
  const listEl = containerEl ? containerEl.querySelector('#sop-list') : null;
  if (!listEl) return;

  if (sops.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u{1F4CB}</div>
        <div class="empty-text">No SOPs found</div>
        <div class="empty-sub">Create a custom SOP with the + New button</div>
      </div>
    `;
    return;
  }

  listEl.innerHTML = sops.map(s => {
    const isSelected = selectedSop === s.name;
    const isBuiltin = s.type === 'builtin';
    const badgeClass = isBuiltin ? 'badge-warning' : 'badge-info';

    return `
      <div class="session-row ${isSelected ? 'selected' : ''}" data-sop="${esc(s.name)}">
        <div class="session-row-icon">${isBuiltin ? '\u{1F512}' : '\u{1F4DD}'}</div>
        <div class="session-row-info">
          <div class="session-row-id">${esc(s.name)}</div>
          <div class="session-row-meta">
            <span class="badge ${badgeClass}">${esc(s.type)}</span>
            ${s.description ? `<span class="text-sm text-muted">${esc(s.description.slice(0, 60))}</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');

  // Click to select
  listEl.querySelectorAll('.session-row').forEach(row => {
    row.addEventListener('click', () => {
      selectedSop = row.dataset.sop;
      _renderSopList();
      _loadSop(selectedSop);
    });
  });
}

async function _loadSop(name) {
  const editorEl = containerEl ? containerEl.querySelector('#sop-editor') : null;
  if (!editorEl) return;
  editorEl.style.display = 'block';

  try {
    const data = await fetchJSON(`/api/sops/${encodeURIComponent(name)}`);
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    sopContent = data.content || '';
    isEditing = false;
    const isBuiltin = data.type === 'builtin';

    _renderEditor(name, sopContent, isBuiltin);
  } catch (e) {
    console.error('[SOPs] Load error:', e);
    showToast('Failed to load SOP', 'error');
  }
}

function _renderEditor(name, content, isBuiltin) {
  const titleEl = containerEl ? containerEl.querySelector('#sop-editor-title') : null;
  const actionsEl = containerEl ? containerEl.querySelector('#sop-editor-actions') : null;
  const contentEl = containerEl ? containerEl.querySelector('#sop-editor-content') : null;
  if (!titleEl || !actionsEl || !contentEl) return;

  titleEl.textContent = name;

  // Actions
  const actions = [];
  if (!isBuiltin) {
    if (isEditing) {
      actions.push(`<button class="btn btn-sm btn-primary" id="sop-save">\u2714 Save</button>`);
      actions.push(`<button class="btn btn-sm btn-ghost" id="sop-cancel">Cancel</button>`);
    } else {
      actions.push(`<button class="btn btn-sm btn-primary" id="sop-edit">\u270E Edit</button>`);
      actions.push(`<button class="btn btn-sm btn-danger" id="sop-delete">\u2716 Delete</button>`);
    }
  } else {
    actions.push(`<span class="badge badge-warning">Read-only (built-in)</span>`);
  }
  actionsEl.innerHTML = actions.join('');

  // Content
  if (isEditing) {
    contentEl.innerHTML = `
      <textarea class="input-field text-mono" id="sop-textarea" rows="20" style="margin:0;resize:vertical;font-size:0.8rem;line-height:1.5">${esc(content)}</textarea>
    `;
  } else {
    // Show as formatted pre block
    contentEl.innerHTML = `
      <pre class="text-mono" style="background:rgba(0,0,0,0.3);padding:14px;border-radius:var(--radius-sm);overflow-x:auto;font-size:0.8rem;line-height:1.5;max-height:calc(100vh - 380px);overflow-y:auto;white-space:pre-wrap;word-break:break-word;margin:0">${esc(content)}</pre>
    `;
  }

  // Wire actions
  const editBtn = containerEl.querySelector('#sop-edit');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      isEditing = true;
      _renderEditor(name, sopContent, isBuiltin);
    });
  }

  const cancelBtn = containerEl.querySelector('#sop-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      isEditing = false;
      _renderEditor(name, sopContent, isBuiltin);
    });
  }

  const saveBtn = containerEl.querySelector('#sop-save');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => _saveSop(name));
  }

  const deleteBtn = containerEl.querySelector('#sop-delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => _confirmDeleteSop(name));
  }
}

async function _saveSop(name) {
  const textarea = containerEl ? containerEl.querySelector('#sop-textarea') : null;
  if (!textarea) return;

  const content = textarea.value;
  if (!content.trim()) {
    showToast('SOP content cannot be empty', 'warning');
    return;
  }

  try {
    const resp = await fetch(`/api/sops/${encodeURIComponent(name)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    const data = await resp.json();

    if (data.error) {
      showToast(data.error, 'error');
      return;
    }

    sopContent = content;
    isEditing = false;
    showToast(`SOP '${name}' saved`, 'success');
    _renderEditor(name, sopContent, false);
    _fetchSops();
  } catch (e) {
    console.error('[SOPs] Save error:', e);
    showToast('Failed to save SOP', 'error');
  }
}

function _startNewSop() {
  const editorEl = containerEl ? containerEl.querySelector('#sop-editor') : null;
  if (!editorEl) return;
  editorEl.style.display = 'block';

  const titleEl = containerEl.querySelector('#sop-editor-title');
  const actionsEl = containerEl.querySelector('#sop-editor-actions');
  const contentEl = containerEl.querySelector('#sop-editor-content');

  titleEl.textContent = 'New SOP';
  actionsEl.innerHTML = `
    <button class="btn btn-sm btn-primary" id="sop-create-save">\u2714 Create</button>
  `;
  contentEl.innerHTML = `
    <div style="margin-bottom:12px">
      <label class="text-sm text-muted">SOP Name (kebab-case)</label>
      <input class="input-field text-mono" id="sop-new-name" placeholder="my-procedure" style="margin-top:4px">
    </div>
    <div>
      <label class="text-sm text-muted">Content (Markdown)</label>
      <textarea class="input-field text-mono" id="sop-new-content" rows="16" style="margin-top:4px;resize:vertical;font-size:0.8rem;line-height:1.5" placeholder="# My Procedure\n\n## Overview\nDescribe what this SOP does...\n\n## Steps\n1. First step\n2. Second step"></textarea>
    </div>
  `;

  containerEl.querySelector('#sop-create-save').addEventListener('click', async () => {
    const nameInput = containerEl.querySelector('#sop-new-name');
    const contentInput = containerEl.querySelector('#sop-new-content');
    if (!nameInput || !contentInput) return;

    const name = nameInput.value.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-');
    const content = contentInput.value.trim();

    if (!name) { showToast('Name is required', 'warning'); return; }
    if (!content) { showToast('Content is required', 'warning'); return; }

    try {
      const resp = await fetch(`/api/sops/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      const data = await resp.json();
      if (data.error) { showToast(data.error, 'error'); return; }

      showToast(`SOP '${name}' created`, 'success');
      selectedSop = name;
      _fetchSops();
      _loadSop(name);
    } catch (e) {
      showToast('Failed to create SOP', 'error');
    }
  });
}

function _confirmDeleteSop(name) {
  showModal(
    'Delete SOP',
    `Are you sure you want to delete SOP '${name}'? This action cannot be undone.`,
    () => _deleteSop(name),
    { confirmText: 'Delete', confirmClass: 'btn-danger' }
  );
}

async function _deleteSop(name) {
  try {
    const resp = await fetch(`/api/sops/${encodeURIComponent(name)}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }
    showToast(`SOP '${name}' deleted`, 'success');
    selectedSop = null;
    sopContent = '';
    isEditing = false;
    const editorEl = containerEl ? containerEl.querySelector('#sop-editor') : null;
    if (editorEl) editorEl.style.display = 'none';
    _fetchSops();
  } catch (e) {
    showToast('Failed to delete SOP', 'error');
  }
}
