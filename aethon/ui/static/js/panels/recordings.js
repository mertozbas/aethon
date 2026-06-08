/**
 * AETHON Dashboard — Session Recordings Panel
 *
 * Lists exported session recordings and shows their timeline, snapshots, and a
 * replay (resume) preview. Backed by /api/sessions/recordings*.
 */

import { esc, fetchJSON } from '../theme.js';

let containerEl = null;
let recordings = [];
let selected = null;        // zip name
let eventLayer = '';        // '' | sys | tool | agent

export function mount(container) {
  containerEl = container;
  recordings = [];
  selected = null;
  eventLayer = '';
  _render();
  _fetchRecordings();
}

export function unmount() {
  containerEl = null;
}

function _fmtSize(n) {
  if (!n && n !== 0) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function _fmtTs(sec) {
  try {
    return new Date(sec * 1000).toLocaleString();
  } catch (e) {
    return '';
  }
}

function _render() {
  if (!containerEl) return;
  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title"><span class="title-icon">\u{1F3AC}</span> Session Recordings</h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="rec-count">0 recordings</span>
        <button class="btn btn-sm btn-ghost" id="rec-refresh" aria-label="Refresh recordings">↻ Refresh</button>
      </div>
    </div>
    <div class="session-layout">
      <div class="glass-card" style="padding:0;overflow-y:auto;max-height:calc(100vh - 240px)">
        <div id="rec-list">
          <div class="empty-state"><div class="empty-icon">\u{1F3AC}</div><div class="empty-text">Loading recordings...</div></div>
        </div>
      </div>
      <div class="glass-card" id="rec-detail" style="display:none">
        <div id="rec-detail-content"></div>
      </div>
    </div>
  `;
  containerEl.querySelector('#rec-refresh').addEventListener('click', _fetchRecordings);
}

async function _fetchRecordings() {
  try {
    const data = await fetchJSON('/api/sessions/recordings');
    recordings = data.recordings || [];
    _renderList();
  } catch (e) {
    console.error('[Recordings] fetch error:', e);
  }
}

function _renderList() {
  const listEl = containerEl && containerEl.querySelector('#rec-list');
  const countEl = containerEl && containerEl.querySelector('#rec-count');
  if (!listEl) return;
  if (countEl) countEl.textContent = `${recordings.length} recording${recordings.length !== 1 ? 's' : ''}`;

  if (recordings.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">\u{1F3AC}</div>
        <div class="empty-text">No recordings yet</div>
        <div class="empty-sub">Enable <code>session_recorder.enabled</code> — a ZIP is exported on shutdown</div>
      </div>`;
    return;
  }

  listEl.innerHTML = recordings.map(r => `
    <div class="session-row ${selected === r.name ? 'selected' : ''}" data-name="${esc(r.name)}">
      <div class="session-row-icon">\u{1F3AC}</div>
      <div class="session-row-info">
        <div class="session-row-id text-mono">${esc(r.session_id)}</div>
        <div class="session-row-meta">
          <span class="text-muted text-sm">${esc(_fmtTs(r.timestamp))}</span>
          <span class="badge badge-info">${esc(_fmtSize(r.size))}</span>
        </div>
      </div>
    </div>
  `).join('');

  listEl.querySelectorAll('.session-row').forEach(row => {
    row.addEventListener('click', () => {
      selected = row.dataset.name;
      eventLayer = '';
      _renderList();
      _showDetail(selected);
    });
  });
}

async function _showDetail(name) {
  const detailEl = containerEl && containerEl.querySelector('#rec-detail');
  const contentEl = containerEl && containerEl.querySelector('#rec-detail-content');
  if (!detailEl || !contentEl) return;
  detailEl.style.display = 'block';
  contentEl.innerHTML = `<div class="empty-state"><div class="empty-text">Loading...</div></div>`;

  try {
    const enc = encodeURIComponent(name);
    const [meta, snaps] = await Promise.all([
      fetchJSON(`/api/sessions/recordings/${enc}`),
      fetchJSON(`/api/sessions/recordings/${enc}/snapshots`),
    ]);
    const snapshots = snaps.snapshots || [];

    contentEl.innerHTML = `
      <h3 style="margin:0 0 12px 0;color:var(--accent-primary)">\u{1F3AC} ${esc(meta.session_id || name)}</h3>
      <div class="detail-grid">
        <div class="detail-item"><span class="detail-label">Events</span><span class="detail-value">${meta.events_count}</span></div>
        <div class="detail-item"><span class="detail-label">Snapshots</span><span class="detail-value">${meta.snapshots_count}</span></div>
        <div class="detail-item"><span class="detail-label">Duration</span><span class="detail-value">${(meta.duration || 0).toFixed(1)}s</span></div>
        <div class="detail-item"><span class="detail-label">Resumable</span><span class="detail-value">${meta.has_resumable_state ? '✓' : '—'}</span></div>
      </div>

      <h4 style="margin:18px 0 8px 0">Snapshots</h4>
      <div id="rec-snapshots">
        ${snapshots.length === 0 ? '<div class="text-muted text-sm">No snapshots</div>' : snapshots.map(s => `
          <div class="glass-card" style="padding:10px;margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
              <span class="text-mono text-sm">#${s.id} · ${esc(_fmtTs(s.timestamp))} · ${s.messages_count} msgs</span>
              <button class="btn btn-sm btn-ghost rec-replay" data-id="${s.id}">▶ Replay</button>
            </div>
            ${s.last_query ? `<div class="text-sm text-muted" style="margin-top:6px">Q: ${esc(s.last_query.slice(0, 160))}</div>` : ''}
          </div>
        `).join('')}
      </div>
      <div id="rec-replay-result"></div>

      <h4 style="margin:18px 0 8px 0">
        Events
        <select id="rec-layer" class="btn btn-sm btn-ghost" style="margin-left:8px">
          <option value="">all</option><option value="tool">tool</option>
          <option value="agent">agent</option><option value="sys">sys</option>
        </select>
      </h4>
      <div id="rec-events"><div class="text-muted text-sm">Loading events...</div></div>
    `;

    contentEl.querySelectorAll('.rec-replay').forEach(btn => {
      btn.addEventListener('click', () => _replay(name, btn.dataset.id));
    });
    const sel = contentEl.querySelector('#rec-layer');
    sel.value = eventLayer;
    sel.addEventListener('change', () => { eventLayer = sel.value; _loadEvents(name); });
    _loadEvents(name);
  } catch (e) {
    contentEl.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠</div><div class="empty-text">Failed to load recording</div></div>`;
  }
}

async function _loadEvents(name) {
  const el = containerEl && containerEl.querySelector('#rec-events');
  if (!el) return;
  try {
    const q = eventLayer ? `?layer=${encodeURIComponent(eventLayer)}` : '';
    const data = await fetchJSON(`/api/sessions/recordings/${encodeURIComponent(name)}/events${q}`);
    const events = (data.events || []).slice(0, 200);
    if (events.length === 0) { el.innerHTML = '<div class="text-muted text-sm">No events</div>'; return; }
    el.innerHTML = `<div style="max-height:340px;overflow-y:auto">${events.map(ev => `
      <div class="text-mono text-sm" style="padding:3px 0;border-bottom:1px solid var(--border-subtle)">
        <span class="badge badge-info">${esc(ev.layer)}</span>
        <span class="text-muted">${esc(ev.event_type)}</span>
        ${esc(JSON.stringify(ev.data).slice(0, 140))}
      </div>`).join('')}</div>`;
  } catch (e) {
    el.innerHTML = '<div class="text-muted text-sm">Failed to load events</div>';
  }
}

async function _replay(name, snapshotId) {
  const el = containerEl && containerEl.querySelector('#rec-replay-result');
  if (!el) return;
  el.innerHTML = '<div class="text-muted text-sm">Resuming...</div>';
  try {
    const res = await fetch(`/api/sessions/recordings/${encodeURIComponent(name)}/replay/${encodeURIComponent(snapshotId)}`,
      { method: 'POST', credentials: 'same-origin' });
    const data = await res.json();
    el.innerHTML = `
      <div class="glass-card" style="padding:12px;margin-top:8px">
        <div style="color:var(--accent-primary);font-weight:600">▶ Resume preview · snapshot #${esc(String(snapshotId))}</div>
        <div class="detail-grid" style="margin-top:8px">
          <div class="detail-item"><span class="detail-label">Status</span><span class="detail-value">${esc(data.status || '')}</span></div>
          <div class="detail-item"><span class="detail-label">Messages</span><span class="detail-value">${esc(String(data.messages_count ?? ''))}</span></div>
          <div class="detail-item"><span class="detail-label">CWD</span><span class="detail-value text-mono">${esc(data.cwd || '')}</span></div>
        </div>
        ${data.continuation_prompt ? `<pre class="text-sm" style="white-space:pre-wrap;margin-top:8px">${esc(data.continuation_prompt.slice(0, 800))}</pre>` : ''}
      </div>`;
  } catch (e) {
    el.innerHTML = '<div class="text-muted text-sm">Replay failed</div>';
  }
}
