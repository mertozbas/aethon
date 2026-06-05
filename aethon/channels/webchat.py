"""WebChat channel adapter.

FastAPI + WebSocket based web chat interface with Markdown rendering.
"""

import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage


# JavaScript is in a raw string so Python does NOT process escape sequences.
# This means \s, \n, \*, \x00 etc. pass through to the browser exactly as written.
_CHAT_SCRIPT = r"""
<script>
const ws = new WebSocket(`ws://${location.host}/ws/chat`);
const msgs = document.getElementById('msgs');
const inp = document.getElementById('inp');

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

ws.onmessage = function(e) { addMsg(e.data, 'bot'); };

function send() {
  var t = inp.value.trim();
  if (!t) return;
  addMsg(t, 'user');
  ws.send(t);
  inp.value = '';
}

inp.addEventListener('keydown', function(e) { if (e.key === 'Enter') send(); });
</script>
"""


class WebChatAdapter(ChannelAdapter):
    """FastAPI + WebSocket based web chat."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.app = FastAPI(title="AETHON")
        self.port = config.channels.webchat.port
        self.host = config.channels.webchat.host
        self._server = None
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def index():
            return HTMLResponse(self._get_chat_html())

        @self.app.websocket("/ws/chat")
        async def ws_chat(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_text()
                    inbound = InboundMessage(
                        channel="webchat",
                        sender_id="local",
                        sender_name="User",
                        text=data,
                    )
                    response = await self.router.handle(inbound)
                    if response:
                        await websocket.send_text(response.text)
            except WebSocketDisconnect:
                pass

        @self.app.get("/api/status")
        async def status():
            return {"status": "running", "version": "0.1.0"}

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
