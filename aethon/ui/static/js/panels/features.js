/**
 * AETHON Dashboard — Features & Capabilities Panel
 *
 * Surfaces every capability/runtime feature and its live on/off status, read
 * from /api/config. Read-only status view (config is applied at startup) with a
 * clear map of what each feature enables and which carry risk.
 */

import { esc, fetchJSON } from '../theme.js';

let containerEl = null;

// Safe nested lookup: get(obj, "a.b.c", default)
function get(obj, path, dflt) {
  let cur = obj;
  for (const k of path.split('.')) {
    if (cur == null || typeof cur !== 'object' || !(k in cur)) return dflt;
    cur = cur[k];
  }
  return cur;
}

// Feature catalog — grouped. `flag` is the config path of the on/off boolean.
const GROUPS = [
  {
    title: 'Capabilities',
    icon: '\u{1F9F0}',
    features: [
      { key: 'scraper', name: 'Web Scraper', flag: 'capabilities.scraper.enabled',
        adds: 'scraper', desc: 'BeautifulSoup HTML/XML scraping & parsing.' },
      { key: 'github', name: 'GitHub GraphQL', flag: 'capabilities.github.enabled',
        adds: 'use_github', desc: 'Query & mutate GitHub via the v4 GraphQL API.' },
      { key: 'jsonrpc', name: 'JSON-RPC', flag: 'capabilities.jsonrpc.enabled',
        adds: 'jsonrpc', desc: 'Call JSON-RPC services over HTTP/WebSocket.' },
      { key: 'notify', name: 'Notifications', flag: 'capabilities.notify.enabled',
        adds: 'notify', desc: 'Native macOS notifications / bell / speech.' },
      { key: 'computer', name: 'Computer Control', flag: 'capabilities.computer.enabled',
        adds: 'use_computer', desc: 'Screen / mouse / keyboard automation (pyautogui).',
        risk: 'Controls your machine. Needs macOS Accessibility permission.' },
    ],
  },
  {
    title: 'macOS Integration',
    icon: '\u{1F34E}',
    features: [
      { key: 'macos', name: 'macOS Tools', flag: 'macos.enabled',
        adds: 'use_mac, apple_notes', desc: 'Calendar, Reminders, Mail, Contacts, Safari, Finder, Shortcuts, Notes.' },
      { key: 'mac_msg', name: 'Messages', flag: 'macos.enable_messages',
        adds: 'use_mac: messages.*', desc: 'Send iMessage / SMS on your behalf.',
        risk: 'Can message people as you.' },
      { key: 'mac_kc', name: 'Keychain', flag: 'macos.enable_keychain',
        adds: 'use_mac: keychain.*', desc: 'Read / write the macOS Keychain.',
        risk: 'Can read & modify stored secrets.' },
    ],
  },
  {
    title: 'Code Intelligence',
    icon: '\u{1F50D}',
    features: [
      { key: 'lsp', name: 'LSP', flag: 'lsp.enabled',
        adds: 'lsp', desc: 'Diagnostics, go-to-definition, references, hover via language servers.' },
      { key: 'lsp_diag', name: 'Auto-Diagnostics', flag: 'lsp.auto_diagnostics',
        adds: 'after-edit hook', desc: 'Append type/error diagnostics after file edits.' },
    ],
  },
  {
    title: 'Runtime & Autonomy',
    icon: '\u{1F916}',
    features: [
      { key: 'rt', name: 'Dynamic Tools', flag: 'runtime_tools.enabled',
        adds: 'manage_tools', desc: 'Create / fetch / install tools at runtime (sandboxed).',
        risk: 'Loads & runs new code (validated in a subprocess sandbox).' },
      { key: 'ambient', name: 'Ambient Mode', flag: 'ambient.enabled',
        adds: 'start/stop/get_ambient', desc: 'Proactive / autonomous work during idle time.' },
      { key: 'rec', name: 'Session Recording', flag: 'session_recorder.enabled',
        adds: 'Recordings tab', desc: 'Record the session timeline & snapshots; replay later.' },
      { key: 'mcp', name: 'MCP Integration', flag: 'mcp.enabled',
        adds: 'external tools', desc: 'Load tools from external MCP servers.' },
    ],
  },
  {
    title: 'System Prompt Awareness',
    icon: '\u{1F9E0}',
    features: [
      { key: 'p_env', name: 'Environment', flag: 'prompt.include_environment',
        adds: 'prompt layer', desc: 'OS / cwd / shell / host injected each turn.' },
      { key: 'p_learn', name: 'Learnings', flag: 'prompt.include_learnings',
        adds: 'record_learning', desc: 'Persistent learnings (LEARNINGS.md) across sessions.' },
      { key: 'p_logs', name: 'Recent Logs', flag: 'prompt.include_recent_logs',
        adds: 'prompt layer', desc: 'Tail of recent activity logs in the prompt.' },
      { key: 'p_shell', name: 'Shell History', flag: 'prompt.include_shell_history',
        adds: 'prompt layer', desc: 'Recent bash/zsh history for continuity.',
        risk: 'Exposes your shell history to the model.' },
      { key: 'p_self', name: 'Self-Awareness', flag: 'prompt.include_self_awareness',
        adds: 'prompt layer', desc: 'Embeds key AETHON source files (heavy — slows turns).' },
    ],
  },
];

export function mount(container) {
  containerEl = container;
  _renderShell();
  _load();
}

export function unmount() {
  containerEl = null;
}

function _renderShell() {
  containerEl.innerHTML = `
    <div class="panel-header">
      <h2 class="panel-title"><span class="title-icon">✨</span> Features &amp; Capabilities</h2>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="text-mono text-sm text-muted" id="feat-summary">—</span>
        <button class="btn btn-sm btn-ghost" id="feat-refresh" aria-label="Refresh">↻</button>
      </div>
    </div>
    <div class="feat-note text-sm text-muted">
      Live status from your config. Settings apply at startup — edit
      <code>~/.aethon/config.yaml</code> and restart to change them.
    </div>
    <div id="feat-body"><div class="empty-state"><div class="empty-text">Loading…</div></div></div>
  `;
  containerEl.querySelector('#feat-refresh').addEventListener('click', _load);
}

async function _load() {
  const body = containerEl && containerEl.querySelector('#feat-body');
  if (!body) return;
  let cfg;
  try {
    cfg = await fetchJSON('/api/config');
  } catch (e) {
    body.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠</div><div class="empty-text">Failed to load config</div></div>`;
    return;
  }

  let total = 0, on = 0;
  const sections = GROUPS.map((g) => {
    const cards = g.features.map((f) => {
      const enabled = !!get(cfg, f.flag, false);
      total++; if (enabled) on++;
      const riskBadge = f.risk
        ? `<span class="feat-risk" title="${esc(f.risk)}">⚠ risk</span>` : '';
      return `
        <div class="feat-card ${enabled ? 'on' : 'off'}">
          <div class="feat-card-head">
            <span class="feat-name">${esc(f.name)}</span>
            <span class="feat-pill ${enabled ? 'on' : 'off'}">${enabled ? 'ON' : 'OFF'}</span>
          </div>
          <div class="feat-desc">${esc(f.desc)}</div>
          <div class="feat-foot">
            <span class="feat-adds text-mono" title="tools / behavior added">+ ${esc(f.adds)}</span>
            ${riskBadge}
          </div>
          <code class="feat-flag">${esc(f.flag)}</code>
        </div>`;
    }).join('');
    const groupOn = g.features.filter((f) => get(cfg, f.flag, false)).length;
    return `
      <section class="feat-group">
        <h3 class="feat-group-title">
          <span>${g.icon}</span> ${esc(g.title)}
          <span class="feat-group-count">${groupOn}/${g.features.length}</span>
        </h3>
        <div class="feat-grid">${cards}</div>
      </section>`;
  }).join('');

  body.innerHTML = sections;
  const summary = containerEl.querySelector('#feat-summary');
  if (summary) summary.textContent = `${on}/${total} enabled`;
}
