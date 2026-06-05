/**
 * AETHON Dashboard — Memory Explorer Panel
 *
 * Browse, search, add, and delete memories.
 * Semantic search with relevance scores, category badges, CRUD operations.
 */

import { esc, fetchJSON, postJSON, formatNumber } from '../theme.js';
import { showToast } from '../components/toast.js';
import { showModal } from '../components/modal.js';

const CATEGORIES = ['general', 'tercih', 'bilgi', 'kural', 'olay', 'beceri'];

let containerEl = null;
let memories = [];
let memoryStats = null;
let searchResults = null;
let searchQuery = '';
let refreshTimer = null;

export function mount(container) {
  containerEl = container;
  memories = [];
  memoryStats = null;
  searchResults = null;
  searchQuery = '';
  _render();
  _fetchMemories();
  _fetchStats();

  // Periodic refresh
  refreshTimer = setInterval(() => {
    if (!searchResults) _fetchMemories();
    _fetchStats();
  }, 30000);
}

export function unmount() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2B50</span>
        Memory Explorer
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="memory-count">-</span>
        <button class="btn btn-sm btn-primary" id="memory-add-btn" aria-label="Add memory">\u2795 Add</button>
        <button class="btn btn-sm btn-ghost" id="memory-refresh" aria-label="Refresh">\u21BB</button>
      </div>
    </div>

    <!-- Stats bar -->
    <div id="memory-stats-bar" class="stats-bar" style="margin-bottom:12px"></div>

    <!-- Search -->
    <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center">
      <div style="flex:1">
        <input class="input-field" id="memory-search" placeholder="Semantic search (e.g., 'user preferences')..." style="margin:0" aria-label="Search memories">
      </div>
      <button class="btn btn-sm btn-primary" id="memory-search-btn" aria-label="Search">\u{1F50D} Search</button>
      <button class="btn btn-sm btn-ghost" id="memory-search-clear" style="display:none" aria-label="Clear search">\u2716 Clear</button>
    </div>

    <!-- Memory list -->
    <div id="memory-list">
      <div class="empty-state">
        <div class="empty-icon">\u2B50</div>
        <div class="empty-text">Loading memories...</div>
      </div>
    </div>

    <!-- Add memory form (hidden) -->
    <div id="memory-add-form" class="glass-card" style="display:none;margin-top:16px">
      <h3 style="margin:0 0 12px 0;color:var(--accent-primary)">\u2795 Add New Memory</h3>
      <div style="margin-bottom:12px">
        <label class="text-sm text-muted" for="memory-add-content">Content</label>
        <textarea class="input-field" id="memory-add-content" rows="3" placeholder="What should AETHON remember?" style="margin-top:4px;resize:vertical"></textarea>
      </div>
      <div style="display:flex;gap:12px;align-items:flex-end;margin-bottom:12px">
        <div style="flex:1">
          <label class="text-sm text-muted" for="memory-add-category">Category</label>
          <select class="input-field" id="memory-add-category" style="margin-top:4px">
            ${CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join('')}
          </select>
        </div>
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn btn-sm btn-ghost" id="memory-add-cancel">Cancel</button>
        <button class="btn btn-sm btn-primary" id="memory-add-save">\u2714 Save</button>
      </div>
    </div>
  `;

  // Event listeners
  containerEl.querySelector('#memory-refresh').addEventListener('click', () => {
    searchResults = null;
    searchQuery = '';
    const searchInput = containerEl.querySelector('#memory-search');
    if (searchInput) searchInput.value = '';
    const clearBtn = containerEl.querySelector('#memory-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    _fetchMemories();
    _fetchStats();
  });

  containerEl.querySelector('#memory-search-btn').addEventListener('click', _doSearch);

  containerEl.querySelector('#memory-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') _doSearch();
  });

  containerEl.querySelector('#memory-search-clear').addEventListener('click', () => {
    searchResults = null;
    searchQuery = '';
    const searchInput = containerEl.querySelector('#memory-search');
    if (searchInput) searchInput.value = '';
    containerEl.querySelector('#memory-search-clear').style.display = 'none';
    _renderMemories();
  });

  containerEl.querySelector('#memory-add-btn').addEventListener('click', () => {
    const form = containerEl.querySelector('#memory-add-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
  });

  containerEl.querySelector('#memory-add-cancel').addEventListener('click', () => {
    containerEl.querySelector('#memory-add-form').style.display = 'none';
    containerEl.querySelector('#memory-add-content').value = '';
  });

  containerEl.querySelector('#memory-add-save').addEventListener('click', _addMemory);
}

async function _fetchMemories() {
  try {
    const data = await fetchJSON('/api/memory');
    if (data.enabled === false) {
      memories = [];
      _renderMemories(true);
      return;
    }
    memories = data.entries || [];
    _renderMemories();
  } catch (e) {
    console.error('[Memory] Fetch error:', e);
  }
}

async function _fetchStats() {
  try {
    const data = await fetchJSON('/api/memory/stats');
    memoryStats = data;
    _renderStats();
  } catch (e) {
    console.error('[Memory] Stats error:', e);
  }
}

function _renderStats() {
  const barEl = containerEl ? containerEl.querySelector('#memory-stats-bar') : null;
  const countEl = containerEl ? containerEl.querySelector('#memory-count') : null;
  if (!barEl || !memoryStats) return;

  if (countEl) {
    countEl.textContent = `${memoryStats.count || 0} memories`;
  }

  if (!memoryStats.enabled) {
    barEl.innerHTML = `<span class="badge badge-warning">Memory Disabled</span>`;
    return;
  }

  const categories = memoryStats.categories || {};
  const dbSize = memoryStats.db_size_bytes || 0;
  const dbSizeStr = dbSize > 1024 * 1024
    ? `${(dbSize / (1024 * 1024)).toFixed(1)}MB`
    : `${(dbSize / 1024).toFixed(1)}KB`;

  barEl.innerHTML = `
    <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">
      <span class="text-mono text-sm" style="color:var(--accent-primary)">${formatNumber(memoryStats.count || 0)} memories</span>
      <span class="text-mono text-sm text-muted">\u2022 ${dbSizeStr}</span>
      ${Object.entries(categories).map(([cat, count]) => `
        <span class="badge badge-ghost">${esc(cat)}: ${count}</span>
      `).join('')}
    </div>
  `;
}

function _renderMemories(disabled = false) {
  const listEl = containerEl ? containerEl.querySelector('#memory-list') : null;
  if (!listEl) return;

  if (disabled) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u26A0</div>
        <div class="empty-text">Memory is not enabled</div>
        <div class="empty-sub">Enable memory in aethon.yaml to use the Memory Explorer</div>
      </div>
    `;
    return;
  }

  const items = searchResults || memories;

  if (items.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u2B50</div>
        <div class="empty-text">${searchResults ? 'No matching memories' : 'No memories stored'}</div>
        <div class="empty-sub">${searchResults ? 'Try a different search query' : 'Click + Add to store a new memory'}</div>
      </div>
    `;
    return;
  }

  listEl.innerHTML = items.map(m => {
    const hasScore = m.score !== undefined;
    const scorePercent = hasScore ? Math.round(m.score * 100) : 0;
    const scoreColor = scorePercent > 80 ? 'var(--color-success)' :
                       scorePercent > 50 ? 'var(--color-warning)' : 'var(--color-error)';

    return `
      <div class="glass-card memory-card" style="margin-bottom:8px;padding:12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
          <div style="flex:1;min-width:0">
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
              <span class="badge badge-info">${esc(m.category || 'general')}</span>
              <span class="text-mono text-sm text-muted">#${m.id}</span>
              ${hasScore ? `<span class="text-mono text-sm" style="color:${scoreColor}">${scorePercent}%</span>` : ''}
              ${m.created_at ? `<span class="text-sm text-muted">${esc(m.created_at.split('T')[0] || '')}</span>` : ''}
            </div>
            <div class="text-sm" style="word-break:break-word">${esc(m.content || '')}</div>
            ${hasScore ? `
              <div style="margin-top:6px;height:3px;background:rgba(255,255,255,0.05);border-radius:2px;overflow:hidden">
                <div style="width:${scorePercent}%;height:100%;background:${scoreColor};border-radius:2px"></div>
              </div>
            ` : ''}
          </div>
          <button class="btn btn-sm btn-ghost memory-delete-btn" data-mid="${m.id}" aria-label="Delete memory #${m.id}" style="flex-shrink:0">
            \u2716
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Delete buttons
  listEl.querySelectorAll('.memory-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const mid = parseInt(btn.dataset.mid);
      _confirmDelete(mid);
    });
  });
}

async function _doSearch() {
  const input = containerEl ? containerEl.querySelector('#memory-search') : null;
  if (!input) return;

  const query = input.value.trim();
  if (!query) return;

  searchQuery = query;

  try {
    const data = await postJSON('/api/memory/search', { query, top_k: 20 });
    searchResults = data.results || [];
    const clearBtn = containerEl.querySelector('#memory-search-clear');
    if (clearBtn) clearBtn.style.display = 'inline-flex';
    _renderMemories();
  } catch (e) {
    console.error('[Memory] Search error:', e);
    showToast('Search failed', 'error');
  }
}

async function _addMemory() {
  const contentEl = containerEl ? containerEl.querySelector('#memory-add-content') : null;
  const categoryEl = containerEl ? containerEl.querySelector('#memory-add-category') : null;
  if (!contentEl || !categoryEl) return;

  const content = contentEl.value.trim();
  if (!content) {
    showToast('Content is required', 'warning');
    return;
  }

  const category = categoryEl.value;

  try {
    const data = await postJSON('/api/memory', { content, category });
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }
    showToast(`Memory #${data.memory_id} stored`, 'success');
    contentEl.value = '';
    containerEl.querySelector('#memory-add-form').style.display = 'none';
    _fetchMemories();
    _fetchStats();
  } catch (e) {
    console.error('[Memory] Add error:', e);
    showToast('Failed to add memory', 'error');
  }
}

function _confirmDelete(memoryId) {
  showModal(
    'Delete Memory',
    `Are you sure you want to delete memory #${memoryId}? This action cannot be undone.`,
    () => _deleteMemory(memoryId),
    { confirmText: 'Delete', confirmClass: 'btn-danger' }
  );
}

async function _deleteMemory(memoryId) {
  try {
    const resp = await fetch(`/api/memory/${memoryId}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.error) {
      showToast(data.error, 'error');
      return;
    }
    showToast(`Memory #${memoryId} deleted`, 'success');
    // Remove from local arrays
    memories = memories.filter(m => m.id !== memoryId);
    if (searchResults) {
      searchResults = searchResults.filter(m => m.id !== memoryId);
    }
    _renderMemories();
    _fetchStats();
  } catch (e) {
    console.error('[Memory] Delete error:', e);
    showToast('Failed to delete memory', 'error');
  }
}
