/**
 * AETHON Dashboard — Configuration Editor Panel
 *
 * Displays current config with masked sensitive fields.
 * Uses JSON Schema to generate form groups.
 */

import { esc, fetchJSON } from '../theme.js';
import { showToast } from '../components/toast.js';

let containerEl = null;
let configData = null;
let schemaData = null;
let expandedSections = new Set(['model', 'channels']);

export function mount(container) {
  containerEl = container;
  configData = null;
  schemaData = null;
  _render();
  _fetchConfig();
  _fetchSchema();
}

export function unmount() {
  containerEl = null;
}

function _render() {
  if (!containerEl) return;

  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title">
        <span class="title-icon">\u2699</span>
        Configuration
      </h2>
      <div style="display:flex;align-items:center;gap:8px">
        <button class="btn btn-sm btn-ghost" id="config-refresh" aria-label="Refresh config">\u21BB Refresh</button>
      </div>
    </div>

    <div class="text-sm text-muted" style="margin-bottom:12px">
      Current AETHON configuration. Sensitive fields (API keys, tokens) are masked.
    </div>

    <div id="config-content">
      <div class="empty-state">
        <div class="empty-icon">\u2699</div>
        <div class="empty-text">Loading configuration...</div>
      </div>
    </div>
  `;

  containerEl.querySelector('#config-refresh').addEventListener('click', () => {
    _fetchConfig();
    _fetchSchema();
  });
}

async function _fetchConfig() {
  try {
    configData = await fetchJSON('/api/config');
    _renderConfig();
  } catch (e) {
    console.error('[Config] Fetch error:', e);
    showToast('Failed to load config', 'error');
  }
}

async function _fetchSchema() {
  try {
    schemaData = await fetchJSON('/api/config/schema');
  } catch (e) {
    console.error('[Config] Schema fetch error:', e);
  }
}

function _renderConfig() {
  const contentEl = containerEl ? containerEl.querySelector('#config-content') : null;
  if (!contentEl || !configData) return;

  const sections = Object.entries(configData);

  contentEl.innerHTML = sections.map(([key, value]) => {
    const isExpanded = expandedSections.has(key);
    const isObject = typeof value === 'object' && value !== null;

    if (!isObject) {
      return `
        <div class="config-item glass-card" style="padding:10px 14px;margin-bottom:6px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span class="text-sm" style="color:var(--accent-primary)">${esc(key)}</span>
            <span class="text-mono text-sm">${_renderValue(value)}</span>
          </div>
        </div>
      `;
    }

    return `
      <div class="glass-card" style="padding:0;margin-bottom:8px;overflow:hidden">
        <div class="config-section-header" data-section="${esc(key)}" style="padding:12px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border-subtle)">
          <span style="font-weight:600;color:var(--accent-primary)">${esc(key)}</span>
          <span class="text-muted" style="font-size:0.8rem">${isExpanded ? '\u25BC' : '\u25B6'} ${Object.keys(value).length} fields</span>
        </div>
        <div class="config-section-body" data-section-body="${esc(key)}" style="display:${isExpanded ? 'block' : 'none'};padding:8px 14px">
          ${_renderObject(value, 0)}
        </div>
      </div>
    `;
  }).join('');

  // Section toggles
  contentEl.querySelectorAll('.config-section-header').forEach(header => {
    header.addEventListener('click', () => {
      const section = header.dataset.section;
      if (expandedSections.has(section)) {
        expandedSections.delete(section);
      } else {
        expandedSections.add(section);
      }
      _renderConfig();
    });
  });
}

function _renderObject(obj, depth) {
  if (!obj || typeof obj !== 'object') return _renderValue(obj);

  return Object.entries(obj).map(([key, value]) => {
    const isNested = typeof value === 'object' && value !== null && !Array.isArray(value);
    const indent = depth * 12;

    if (isNested) {
      return `
        <div style="margin-left:${indent}px;margin-bottom:4px">
          <div class="text-sm" style="color:var(--accent-secondary);margin-bottom:4px;margin-top:8px">${esc(key)}:</div>
          ${_renderObject(value, depth + 1)}
        </div>
      `;
    }

    return `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;margin-left:${indent}px;border-bottom:1px solid rgba(255,255,255,0.02)">
        <span class="text-sm text-muted">${esc(key)}</span>
        <span class="text-mono text-sm">${_renderValue(value)}</span>
      </div>
    `;
  }).join('');
}

function _renderValue(value) {
  if (value === null || value === undefined) return '<span class="text-muted">null</span>';
  if (value === '***') return '<span style="color:var(--color-warning)">\u2022\u2022\u2022 masked</span>';
  if (typeof value === 'boolean') {
    return value
      ? '<span style="color:var(--color-success)">true</span>'
      : '<span style="color:var(--color-error)">false</span>';
  }
  if (typeof value === 'number') return `<span style="color:var(--accent-warm)">${value}</span>`;
  if (Array.isArray(value)) {
    if (value.length === 0) return '<span class="text-muted">[]</span>';
    return `<span class="text-muted">[${value.length} items]</span>`;
  }
  if (typeof value === 'object') return '<span class="text-muted">{...}</span>';
  const str = String(value);
  if (str.length > 60) return esc(str.slice(0, 60)) + '...';
  return esc(str);
}
