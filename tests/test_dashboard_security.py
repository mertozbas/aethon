"""Tests for dashboard auth, thread-safe event delivery, and memory locking (Step 4)."""

import asyncio
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from aethon.config import AethonConfig
from aethon.ui.dashboard import setup_dashboard
from aethon.ui.event_bus import DashboardEventBus


def _dashboard_app(token: str = ""):
    app = FastAPI()
    cfg = AethonConfig()
    cfg.dashboard.auth_token = token
    runtime = MagicMock()
    runtime.agents = {}
    runtime.memory = None
    setup_dashboard(app, runtime, cfg, event_bus=None)
    return app


# --- Auth -----------------------------------------------------------------


def test_no_token_means_open():
    client = TestClient(_dashboard_app(token=""))
    assert client.get("/api/config").status_code == 200


def test_api_blocked_without_token():
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/api/config").status_code == 401


def test_api_allowed_with_bearer_header():
    client = TestClient(_dashboard_app(token="secret"))
    r = client.get("/api/config", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200


def test_api_allowed_with_query_token():
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/api/config?token=secret").status_code == 200


def test_api_rejected_with_wrong_token():
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/api/config?token=nope").status_code == 401


def test_dashboard_page_gated_and_sets_cookie():
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/dashboard").status_code == 401
    r = client.get("/dashboard?token=secret")
    assert r.status_code == 200
    assert r.cookies.get("aethon_dash") == "secret"


def test_webchat_style_status_not_gated_by_dashboard_auth():
    # The dashboard auth must only gate dashboard paths, not arbitrary /api/* a
    # co-mounted app might add. /api/status is not in the protected prefixes.
    app = _dashboard_app(token="secret")

    @app.get("/api/status")
    async def status():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/status").status_code == 200


def test_health_open_even_with_dashboard_auth():
    """Health probe must stay reachable when a dashboard token is set.

    Mirrors the gateway wiring: the dashboard is mounted onto the WebChat app,
    so /health (defined on WebChat) shares the auth middleware but must not be gated.
    """
    from aethon.channels.webchat import WebChatAdapter

    cfg = AethonConfig()
    cfg.dashboard.auth_token = "secret"
    adapter = WebChatAdapter(cfg, MagicMock())
    runtime = MagicMock()
    runtime.agents = {}
    runtime.memory = None
    setup_dashboard(adapter.app, runtime, cfg, event_bus=None)

    client = TestClient(adapter.app)
    assert client.get("/health").status_code == 200       # open for healthchecks
    assert client.get("/api/config").status_code == 401    # dashboard API still gated


# --- Thread-safe event delivery -------------------------------------------


@pytest.mark.asyncio
async def test_emit_from_worker_thread_is_delivered():
    bus = DashboardEventBus()
    q = bus.subscribe()  # captures the running loop

    # Emit from a different thread (as the agent's executor worker does).
    threading.Thread(target=lambda: bus.emit("messages", {"x": 1})).start()

    event = await asyncio.wait_for(q.get(), timeout=2.0)
    assert event == {"channel": "messages", "data": {"x": 1}}


# --- VectorMemory write lock ----------------------------------------------


def test_vector_memory_concurrent_writes(tmp_path, monkeypatch):
    from aethon.memory.vector import VectorMemory

    vm = VectorMemory(str(tmp_path / "mem.sqlite"))
    monkeypatch.setattr(vm, "_get_embedding", lambda text: [0.1, 0.2, 0.3])

    threads = [threading.Thread(target=lambda i=i: vm.store(f"mem {i}", "test")) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert vm.count() == 20
    vm.close()
