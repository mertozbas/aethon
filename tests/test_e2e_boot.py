"""End-to-end boot smoke: the real `aethon start` serves over HTTP + WebSocket.

Uses the offline ``echo`` provider so no model backend (Meridian / API key) is needed.
Marked ``e2e`` (it spawns a subprocess and binds a socket) — deselect with
``pytest -m 'not e2e'``.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _get(url: str, timeout: float = 2.0):
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.status, resp.read()
    except Exception as exc:  # connection refused while booting, HTTP errors, etc.
        return getattr(exc, "code", None), b""


@pytest.mark.e2e
def test_aethon_start_serves_end_to_end(tmp_path):
    """`aethon start` boots the gateway and serves health, dashboard, and chat WS."""
    port = _free_port()
    config = tmp_path / "config.yaml"
    config.write_text(
        "model:\n"
        "  provider: echo\n"
        "  model_id: claude-opus-4-8\n"
        "meridian:\n"
        "  auto_start: false\n"
        "channels:\n"
        "  cli:\n"
        "    enabled: false\n"
        "  webchat:\n"
        "    enabled: true\n"
        "    host: 127.0.0.1\n"
        f"    port: {port}\n"
        "memory:\n"
        "  enabled: false\n"
    )

    env = dict(os.environ, HOME=str(tmp_path))  # keep workspace/state out of the real ~/.aethon
    log_path = tmp_path / "server.log"
    base = f"http://127.0.0.1:{port}"

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            [sys.executable, "-m", "aethon", "start", "-c", str(config)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    try:
        # Wait for the server to come up (boot + uvicorn bind), up to ~30s.
        up = False
        for _ in range(60):
            if proc.poll() is not None:  # process died early
                break
            if _get(base + "/health", timeout=1)[0] == 200:
                up = True
                break
            time.sleep(0.5)

        assert up, f"server did not come up. Log:\n{log_path.read_text()}"

        # HTTP surface.
        status, body = _get(base + "/health")
        assert status == 200
        assert json.loads(body) == {"status": "ok"}
        assert _get(base + "/dashboard")[0] == 200          # SPA shell
        assert _get(base + "/")[0] == 200                   # chat UI

        # WebSocket chat round-trip through the echo model.
        from websockets.sync.client import connect

        with connect(f"ws://127.0.0.1:{port}/ws/chat") as ws:
            ws.send("ping from e2e")
            reply = ws.recv()
        assert isinstance(reply, str) and reply.strip()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
