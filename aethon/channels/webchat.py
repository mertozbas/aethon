"""WebChat channel adapter.

FastAPI + WebSocket based web chat interface with Markdown rendering.
"""

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from aethon import __version__
from aethon.channels.base import (
    ApprovalRequest,
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    build_error_reply,
)
from aethon.gateway.netsec import install_auth_gate, origin_allowed, token_ok


logger = logging.getLogger("aethon.webchat")


# JavaScript is in a raw string so Python does NOT process escape sequences.
# This means \s, \n, \*, \x00 etc. pass through to the browser exactly as written.
_CHAT_SCRIPT = r"""
<script>
const msgs = document.getElementById('msgs');
const inp = document.getElementById('inp');
let ws = null;
let wsOpened = false;

function wsUrl() {
  // Proto-aware (wss: behind TLS) + optional auth token from sessionStorage.
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var tok = sessionStorage.getItem('aethon_token');
  return proto + '//' + location.host + '/ws/chat' + (tok ? '?token=' + encodeURIComponent(tok) : '');
}

function connect() {
  wsOpened = false;
  ws = new WebSocket(wsUrl());
  ws.onopen = function() { wsOpened = true; };
  ws.onmessage = function(e) {
    // Approval cards arrive as {"type":"approval",...}; everything else is a
    // bot reply (plain text). Only intercept well-formed approval frames.
    try {
      var obj = JSON.parse(e.data);
      if (obj && obj.type === 'approval') { showApproval(obj); return; }
    } catch (err) { /* not JSON — a normal reply */ }
    addMsg(e.data, 'bot');
  };
  ws.onclose = function() {
    // Auth rejection closes the socket before it ever opens. (Browsers can't
    // see the 1008 close code on a pre-accept rejection — they report 1006 —
    // so we key off "never opened" instead.)
    if (!wsOpened) {
      var t = prompt("AETHON erişim token'ı:");
      if (t) { sessionStorage.setItem('aethon_token', t.trim()); connect(); }
    }
  };
}

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderMd(text) {
  var parts = text.split(/(```[\s\S]*?```)/g);
  var html = '';
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (part.startsWith('```') && part.endsWith('```')) {
      var code = part.slice(3, -3).replace(/^[^\n]*\n?/, '');
      html += '<pre><code>' + esc(code) + '<\/code><\/pre>';
    } else {
      var lines = part.split('\n');
      var rendered = [];
      for (var j = 0; j < lines.length; j++) {
        var line = lines[j];
        var hm = line.match(/^(#{1,6})\s+(.+)$/);
        if (hm) { rendered.push('<b>' + inlineMd(hm[2]) + '<\/b>'); continue; }
        if (/^\s*[-*_]{3,}\s*$/.test(line)) { rendered.push('<hr style="border-color:#333;margin:8px 0">'); continue; }
        rendered.push(inlineMd(line));
      }
      html += rendered.join('<br>');
    }
  }
  return html;
}

function inlineMd(t) {
  // Protect inline code first
  var codes = [];
  t = t.replace(/`([^`]+)`/g, function(_, c) {
    codes.push('<code>' + esc(c) + '<\/code>');
    return '\x00C' + (codes.length - 1);
  });
  // Escape HTML in remaining text (not inside code placeholders)
  var segs = t.split(/(\x00C\d+)/g);
  var out = '';
  for (var i = 0; i < segs.length; i++) {
    if (/^\x00C\d+$/.test(segs[i])) { out += segs[i]; }
    else { out += esc(segs[i]); }
  }
  t = out;
  // Bold: **text** or __text__
  t = t.replace(/\*\*(.+?)\*\*/g, '<b>$1<\/b>');
  t = t.replace(/__(.+?)__/g, '<b>$1<\/b>');
  // Italic: *text* or _text_ (not inside words)
  t = t.replace(/(^|[\s(])\*([^*]+?)\*(?=[\s).,!?]|$)/g, '$1<i>$2<\/i>');
  t = t.replace(/(^|[\s(])_([^_]+?)_(?=[\s).,!?]|$)/g, '$1<i>$2<\/i>');
  // Strikethrough: ~~text~~
  t = t.replace(/~~(.+?)~~/g, '<s>$1<\/s>');
  // Links: [text](url)
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1<\/a>');
  // Restore inline code
  for (var i = 0; i < codes.length; i++) {
    t = t.replace('\x00C' + i, codes[i]);
  }
  return t;
}

function addMsg(text, cls) {
  var d = document.createElement('div');
  d.className = 'msg ' + cls;
  if (cls === 'bot') {
    d.innerHTML = renderMd(text);
  } else {
    d.textContent = text;
  }
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

function showApproval(obj) {
  var d = document.createElement('div');
  d.className = 'msg bot';
  d.innerHTML = '<b>Onay gerekiyor</b><br>' + esc(obj.message || '');
  var row = document.createElement('div');
  row.style.marginTop = '8px';
  var yes = document.createElement('button');
  yes.textContent = '✅ Onayla';
  var no = document.createElement('button');
  no.textContent = '❌ Reddet';
  no.style.marginLeft = '8px';
  function answer(decision) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'approval', id: obj.id, decision: decision }));
    }
    yes.disabled = true; no.disabled = true;
    var verdict = document.createElement('div');
    verdict.style.marginTop = '6px';
    verdict.style.color = decision ? '#4ec9b0' : '#f48771';
    verdict.textContent = decision ? 'Onaylandı' : 'Reddedildi';
    d.appendChild(verdict);
  }
  yes.onclick = function() { answer(true); };
  no.onclick = function() { answer(false); };
  row.appendChild(yes); row.appendChild(no);
  d.appendChild(row);
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

function send() {
  var t = inp.value.trim();
  if (!t || !ws || ws.readyState !== WebSocket.OPEN) return;
  addMsg(t, 'user');
  ws.send(t);
  inp.value = '';
}

inp.addEventListener('keydown', function(e) { if (e.key === 'Enter') send(); });
connect();
</script>
"""


class WebChatAdapter(ChannelAdapter):
    """FastAPI + WebSocket based web chat."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.app = FastAPI(title="AETHON")
        self.port = config.channels.webchat.port
        self.host = config.channels.webchat.host
        # Shared token (dashboard.auth_token). Installed at app construction so
        # the deny-by-default gate exists even when the dashboard is disabled.
        self._auth_token = config.dashboard.auth_token
        self._allowed_origins = config.channels.webchat.allowed_origins
        install_auth_gate(self.app, self._auth_token)
        self._server = None
        # S6 approval: the live chat socket + pending approval futures keyed by
        # interrupt id. WebChat is single local user, so one active socket.
        self._socket: WebSocket | None = None
        self._pending: dict[str, asyncio.Future] = {}
        # Turn serialization now lives at the runtime per session_id (H1), which
        # gates all "webchat:local" turns; the receive loop stays free (tasks
        # await the runtime lock, not the loop) so an in-turn approval is read.
        self._turn_tasks: set = set()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def index():
            return HTMLResponse(self._get_chat_html())

        @self.app.websocket("/ws/chat")
        async def ws_chat(websocket: WebSocket):
            # Reject BEFORE accept(): HTTP middleware never sees WS upgrades,
            # so the websocket gates itself (same pattern as /ws/dashboard).
            # Origin first — a cross-site page must be rejected even if it
            # somehow holds the token (drive-by/CSWSH posture).
            origin = websocket.headers.get("origin")
            if not origin_allowed(
                origin, websocket.headers.get("host", ""), self._allowed_origins
            ):
                logger.warning(f"WS /ws/chat rejected: origin {origin!r} not allowed")
                await websocket.close(code=1008)
                return
            if not token_ok(websocket, self._auth_token):
                await websocket.close(code=1008)
                return
            await websocket.accept()
            # A new connection supersedes any previous one — deny its in-flight
            # approvals so a stale card on the old tab can't linger or cross.
            if self._socket is not None and self._socket is not websocket:
                self._reject_pending()
            self._socket = websocket
            try:
                while True:
                    data = await websocket.receive_text()
                    # Approval responses resolve a pending future, not a chat
                    # turn — intercept them before they become a message.
                    if self._maybe_resolve_approval(data):
                        continue
                    inbound = InboundMessage(
                        channel="webchat",
                        sender_id="local",
                        sender_name="User",
                        text=data,
                    )
                    # Run the turn as a task so the receive loop stays free to
                    # read the approval answer mid-turn (otherwise an in-turn
                    # approval would deadlock: the turn waits for an answer the
                    # blocked socket can't read).
                    # Keep a strong reference: asyncio only weakly references
                    # tasks, so an unreferenced task can be GC'd mid-flight.
                    task = asyncio.create_task(self._run_turn(websocket, inbound))
                    self._turn_tasks.add(task)
                    task.add_done_callback(self._turn_tasks.discard)
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass  # client closed or server shutting down — not an error
            finally:
                self._reject_pending()
                if self._socket is websocket:
                    self._socket = None

        @self.app.get("/api/status")
        async def status():
            return {"status": "running", "version": __version__}

        @self.app.get("/health")
        async def health():
            # Lightweight liveness probe. Enumerated in netsec.PUBLIC_PATHS so the
            # deny-by-default gate leaves it open even when a token is set
            # (Docker HEALTHCHECK / load-balancer probes).
            return {"status": "ok"}

    async def start(self) -> None:
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self) -> None:
        if self._server:
            self._server.should_exit = True

    async def send(self, message: OutboundMessage) -> None:
        pass  # WebSocket sends response directly

    async def _run_turn(self, websocket: WebSocket, inbound: InboundMessage) -> None:
        """Process one turn and send the reply (run as a task so the receive
        loop stays free to read an in-turn approval answer).

        Two overlapping messages are serialized by the runtime's per-session
        lock (H1) — both webchat turns resolve to "webchat:local" — so they can't
        race the shared agent; an in-turn approval still resolves because the
        receive loop (not the turn) reads the answer.
        """
        try:
            try:
                response = await self.router.handle(inbound)
            except (WebSocketDisconnect, asyncio.CancelledError):
                raise
            except Exception as e:
                # H2: a failed turn must reach the browser, not vanish.
                logger.error(f"WebChat turn error: {type(e).__name__}: {e}", exc_info=True)
                response = build_error_reply(inbound, e)
            if response:
                await websocket.send_text(response.text)
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    async def ask_approval(self, request: ApprovalRequest):
        """Send an approval card over the live socket and await the answer (S6).

        Returns True/False, or None when no browser is connected (fail closed).
        The runtime's timeout cancels the await; the disconnect path rejects any
        outstanding futures so a blocked turn never hangs.
        """
        ws = self._socket
        if ws is None:
            return None  # no live browser → can't answer → runtime denies
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[request.interrupt_id] = fut
        try:
            await ws.send_text(json.dumps({
                "type": "approval",
                "id": request.interrupt_id,
                "tool": request.tool,
                "message": request.message,
            }))
            return await fut
        finally:
            self._pending.pop(request.interrupt_id, None)

    def _maybe_resolve_approval(self, data: str) -> bool:
        """Resolve a pending approval if ``data`` is an approval-response frame.

        Returns True when the frame was an approval response (swallowed, not a
        chat turn). Only intercepts well-formed ``{"type":"approval"}`` JSON so
        ordinary chat text — even text that happens to be JSON — flows through.
        """
        try:
            obj = json.loads(data)
        except (ValueError, TypeError):
            return False
        if not (isinstance(obj, dict) and obj.get("type") == "approval"):
            return False
        fut = self._pending.get(obj.get("id"))
        if fut is not None and not fut.done():
            fut.set_result(bool(obj.get("decision")))
        return True  # swallow even an unknown id — it is not chat

    def _reject_pending(self) -> None:
        """Deny all outstanding approvals (e.g. on disconnect) so turns unblock."""
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_result(False)
        self._pending.clear()

    def _get_chat_html(self) -> str:
        """Minimal chat UI HTML with Markdown rendering."""
        return """<!DOCTYPE html>
<html><head>
<title>AETHON</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: system-ui; background: #0a0a0a; color: #e0e0e0;
         display:flex; justify-content:center; align-items:center; height:100vh; }
  .chat { width:700px; height:90vh; display:flex; flex-direction:column;
          border:1px solid #333; border-radius:12px; overflow:hidden; }
  .header { padding:16px; background:#111; border-bottom:1px solid #333;
            font-size:18px; font-weight:bold; color:#00d4ff; }
  .messages { flex:1; overflow-y:auto; padding:16px; }
  .msg { margin:8px 0; padding:10px 14px; border-radius:8px; max-width:80%;
         line-height:1.5; word-wrap:break-word; }
  .user { background:#1a3a5c; margin-left:auto; }
  .bot { background:#1a1a2e; }
  .msg code { background:#2a2a3e; padding:2px 6px; border-radius:4px; font-size:13px;
              font-family:'SF Mono',Consolas,monospace; }
  .msg pre { background:#111; padding:10px; border-radius:6px; margin:6px 0;
             overflow-x:auto; font-size:13px; font-family:'SF Mono',Consolas,monospace; }
  .msg pre code { background:none; padding:0; }
  .msg b { color:#00d4ff; }
  .msg a { color:#00d4ff; text-decoration:underline; }
  .input-area { display:flex; padding:12px; border-top:1px solid #333; background:#111; }
  input { flex:1; padding:10px; border:1px solid #333; border-radius:8px;
          background:#0a0a0a; color:#e0e0e0; font-size:14px; outline:none; }
  button { margin-left:8px; padding:10px 20px; border:none; border-radius:8px;
           background:#00d4ff; color:#000; font-weight:bold; cursor:pointer; }
</style>
</head><body>
<div class="chat">
  <div class="header">AETHON</div>
  <div class="messages" id="msgs"></div>
  <div class="input-area">
    <input id="inp" placeholder="Type your message..." autofocus>
    <button onclick="send()">Send</button>
  </div>
</div>
""" + _CHAT_SCRIPT + "</body></html>"
