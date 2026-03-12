"""Web dashboard for AETHON monitoring.

Provides API endpoints and a real-time UI for monitoring
sessions, memory, telemetry, and scheduled jobs.
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


logger = logging.getLogger("aethon.dashboard")


def setup_dashboard(app, runtime, config):
    """Register dashboard routes on the FastAPI app.

    Args:
        app: FastAPI application instance.
        runtime: AethonRuntime for data access.
        config: AethonConfig.
    """

    @app.get("/dashboard")
    async def dashboard():
        """Dashboard HTML page."""
        return HTMLResponse(_get_dashboard_html())

    @app.get("/api/sessions")
    async def api_sessions():
        """List active sessions."""
        sessions = []
        for sid, agent in runtime.agents.items():
            sessions.append({
                "session_id": sid,
                "agent_name": getattr(agent, "name", "AETHON"),
            })
        return {"sessions": sessions, "count": len(sessions)}

    @app.get("/api/memory")
    async def api_memory():
        """Memory statistics and recent entries."""
        if not runtime.memory:
            return {"enabled": False, "count": 0, "entries": []}
        entries = runtime.memory.list_all(limit=20)
        return {
            "enabled": True,
            "count": runtime.memory.count(),
            "entries": entries,
        }

    @app.post("/api/memory/search")
    async def api_memory_search(request_body: dict):
        """Search memory."""
        if not runtime.memory:
            return {"results": []}
        query = request_body.get("query", "")
        if not query:
            return {"results": []}
        results = runtime.memory.search(query, top_k=10)
        return {"results": results}

    @app.get("/api/config")
    async def api_config():
        """Current configuration."""
        return config.model_dump()

    @app.get("/api/scheduler/jobs")
    async def api_scheduler_jobs():
        """List scheduled jobs."""
        from aethon.tools.scheduler import _scheduler_instance
        if not _scheduler_instance:
            return {"jobs": []}
        return {"jobs": _scheduler_instance.list_jobs()}

    @app.get("/api/telemetry")
    async def api_telemetry():
        """Telemetry summary and recent metrics."""
        telemetry_hook = getattr(runtime, "_telemetry_hook", None)
        if not telemetry_hook:
            return {"enabled": False, "summary": {}, "metrics": []}
        return {
            "enabled": True,
            "summary": telemetry_hook.get_summary(),
            "metrics": telemetry_hook.get_metrics(limit=50),
        }

    @app.websocket("/ws/telemetry")
    async def ws_telemetry(websocket: WebSocket):
        """Real-time telemetry stream."""
        await websocket.accept()
        last_count = 0
        try:
            while True:
                telemetry_hook = getattr(runtime, "_telemetry_hook", None)
                if telemetry_hook:
                    current_count = len(telemetry_hook.metrics)
                    if current_count > last_count:
                        new_metrics = list(telemetry_hook.metrics)[last_count:]
                        for m in new_metrics:
                            await websocket.send_text(json.dumps(m))
                        last_count = current_count
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            pass


_DASHBOARD_SCRIPT = r"""
<script>
const sessionsEl = document.getElementById('sessions');
const memoryEl = document.getElementById('memory');
const telemetryEl = document.getElementById('telemetry');
const jobsEl = document.getElementById('jobs');
const memSearchInput = document.getElementById('mem-search');
const memResultsEl = document.getElementById('mem-results');

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function fetchJSON(url) {
  const r = await fetch(url);
  return r.json();
}

async function refreshSessions() {
  const d = await fetchJSON('/api/sessions');
  if (d.count === 0) { sessionsEl.innerHTML = '<span class="dim">Aktif oturum yok</span>'; return; }
  sessionsEl.innerHTML = d.sessions.map(function(s) {
    return '<div class="card">' + esc(s.session_id) + '</div>';
  }).join('');
}

async function refreshMemory() {
  const d = await fetchJSON('/api/memory');
  if (!d.enabled) { memoryEl.innerHTML = '<span class="dim">Devre disi</span>'; return; }
  memoryEl.innerHTML = '<b>' + d.count + ' kayit</b>';
  if (d.entries.length > 0) {
    memoryEl.innerHTML += d.entries.slice(0,5).map(function(e) {
      return '<div class="card">' + esc(e.content || e.text || JSON.stringify(e)).substring(0,80) + '</div>';
    }).join('');
  }
}

async function refreshTelemetry() {
  const d = await fetchJSON('/api/telemetry');
  if (!d.enabled) { telemetryEl.innerHTML = '<span class="dim">Devre disi</span>'; return; }
  var s = d.summary;
  telemetryEl.innerHTML =
    '<div class="stat">Tool: <b>' + (s.total_tool_calls||0) + '</b></div>' +
    '<div class="stat">Model: <b>' + (s.total_model_calls||0) + '</b></div>' +
    '<div class="stat">Hata: <b>' + (s.error_count||0) + '</b></div>' +
    '<div class="stat">Ort Tool: <b>' + (s.avg_tool_duration||0).toFixed(2) + 's</b></div>' +
    '<div class="stat">Ort Model: <b>' + (s.avg_model_duration||0).toFixed(2) + 's</b></div>';
}

async function refreshJobs() {
  const d = await fetchJSON('/api/scheduler/jobs');
  if (d.jobs.length === 0) { jobsEl.innerHTML = '<span class="dim">Zamanlanmis gorev yok</span>'; return; }
  jobsEl.innerHTML = d.jobs.map(function(j) {
    return '<div class="card"><b>' + esc(j.job_id) + '</b> ' + esc(j.sop_name) + ' (' + esc(j.cron) + ')</div>';
  }).join('');
}

async function searchMemory() {
  var q = memSearchInput.value.trim();
  if (!q) { memResultsEl.innerHTML = ''; return; }
  const r = await fetch('/api/memory/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query: q})
  });
  const d = await r.json();
  if (d.results.length === 0) { memResultsEl.innerHTML = '<span class="dim">Sonuc yok</span>'; return; }
  memResultsEl.innerHTML = d.results.map(function(e) {
    return '<div class="card">' + esc(e.content || e.text || JSON.stringify(e)).substring(0,120) + '</div>';
  }).join('');
}

function refreshAll() {
  refreshSessions();
  refreshMemory();
  refreshTelemetry();
  refreshJobs();
}

refreshAll();
setInterval(refreshAll, 5000);

// WebSocket telemetry stream
var wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
var ws = new WebSocket(wsProto + '//' + location.host + '/ws/telemetry');
var wsLog = document.getElementById('ws-log');
ws.onmessage = function(e) {
  var m = JSON.parse(e.data);
  var d = document.createElement('div');
  d.className = 'ws-entry';
  d.textContent = (m.type||'?') + ' | ' + (m.name||'-') + ' | ' + (m.duration ? m.duration.toFixed(3) + 's' : '-') + ' | ' + (m.status||'-');
  wsLog.insertBefore(d, wsLog.firstChild);
  if (wsLog.children.length > 50) wsLog.removeChild(wsLog.lastChild);
};

memSearchInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') searchMemory(); });
</script>
"""


def _get_dashboard_html() -> str:
    """Dashboard HTML with glassmorphism + cyberpunk neon theme."""
    return """<!DOCTYPE html>
<html><head>
<title>AETHON Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: system-ui; background: #0a0a0a; color: #e0e0e0;
         padding: 24px; min-height: 100vh; }
  h1 { color: #00d4ff; font-size: 28px; margin-bottom: 24px;
       text-shadow: 0 0 20px rgba(0,212,255,0.3); }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .panel { background: rgba(20,20,40,0.8); border: 1px solid rgba(0,212,255,0.2);
           border-radius: 12px; padding: 20px; backdrop-filter: blur(10px); }
  .panel h2 { color: #00d4ff; font-size: 16px; margin-bottom: 12px;
              border-bottom: 1px solid rgba(0,212,255,0.15); padding-bottom: 8px; }
  .card { background: rgba(26,26,46,0.6); padding: 8px 12px; border-radius: 6px;
          margin: 6px 0; font-size: 13px; border-left: 2px solid #00d4ff; }
  .stat { display: inline-block; margin: 4px 12px 4px 0; font-size: 14px; }
  .stat b { color: #00d4ff; }
  .dim { color: #666; font-style: italic; }
  input { padding: 8px 12px; border: 1px solid #333; border-radius: 6px;
          background: #0a0a0a; color: #e0e0e0; font-size: 13px; outline: none;
          width: 100%; margin-bottom: 8px; }
  input:focus { border-color: #00d4ff; }
  .ws-entry { font-family: 'SF Mono', Consolas, monospace; font-size: 12px;
              padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.05);
              color: #aaa; }
  .full-width { grid-column: 1 / -1; }
  @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
</style>
</head><body>
<h1>AETHON Dashboard</h1>
<div class="grid">
  <div class="panel">
    <h2>Oturumlar</h2>
    <div id="sessions"><span class="dim">Yukleniyor...</span></div>
  </div>
  <div class="panel">
    <h2>Hafiza</h2>
    <div id="memory"><span class="dim">Yukleniyor...</span></div>
    <input id="mem-search" placeholder="Hafizada ara..." style="margin-top:12px">
    <div id="mem-results"></div>
  </div>
  <div class="panel">
    <h2>Telemetri</h2>
    <div id="telemetry"><span class="dim">Yukleniyor...</span></div>
  </div>
  <div class="panel">
    <h2>Zamanlanmis Gorevler</h2>
    <div id="jobs"><span class="dim">Yukleniyor...</span></div>
  </div>
  <div class="panel full-width">
    <h2>Canli Metrikler</h2>
    <div id="ws-log" style="max-height:200px;overflow-y:auto"><span class="dim">WebSocket baglantisi bekleniyor...</span></div>
  </div>
</div>
""" + _DASHBOARD_SCRIPT + "</body></html>"
