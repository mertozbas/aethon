"""Tests for dashboard auth, thread-safe event delivery, and memory locking (Step 4).

Phase 9A / S1: the auth middleware is installed at app construction
(WebChatAdapter -> netsec.install_auth_gate) and protects ALL routes by default,
with enumerated public exceptions. The helper below therefore builds the real
shared app (WebChatAdapter + setup_dashboard), mirroring the gateway wiring —
a bare FastAPI() would silently carry no middleware and the tests would pass
vacuously.
"""

import asyncio
import threading

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from aethon.config import AethonConfig
from aethon.channels.webchat import WebChatAdapter
from aethon.ui.dashboard import setup_dashboard
from aethon.ui.event_bus import DashboardEventBus


def _dashboard_app(token: str = "", event_bus=None):
    cfg = AethonConfig()
    cfg.dashboard.auth_token = token
    adapter = WebChatAdapter(cfg, MagicMock())
    runtime = MagicMock()
    runtime.agents = {}
    runtime.memory = None
    setup_dashboard(adapter.app, runtime, cfg, event_bus=event_bus)
    return adapter.app


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


def test_status_gated_by_inverted_middleware():
    """Deny-by-default (S1): /api/status is protected — the old allowlist
    middleware deliberately left it open; the inversion flips that pin."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/api/status").status_code == 401
    assert (
        client.get("/api/status", headers={"Authorization": "Bearer secret"}).status_code
        == 200
    )


def test_health_open_even_with_dashboard_auth():
    """Health probe must stay reachable when a token is set (Docker HEALTHCHECK)."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/health").status_code == 200       # open for healthchecks
    assert client.get("/api/config").status_code == 401    # API still gated


def test_chat_page_open_with_dashboard_auth():
    """The chat page is an enumerated public exception (its WS is gated)."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/").status_code == 200


def test_dashboard_static_public_with_token():
    """SPA assets stay public — enumerated exception (no confidentiality value)."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/dashboard/static/index.html").status_code == 200


def test_unknown_path_gated_returns_401():
    """Deny by default: even unknown paths answer 401, not 404 (no route leaks)."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/definitely-not-a-route").status_code == 401


def test_openapi_docs_gated():
    """FastAPI auto-docs enumerate the whole surface — they require the token."""
    client = TestClient(_dashboard_app(token="secret"))
    assert client.get("/openapi.json").status_code == 401
    assert client.get("/docs").status_code == 401


def test_webhook_paths_exempt_from_dashboard_token():
    """/webhook/* self-authenticates via HMAC (S3) — the dashboard token must
    not gate it, or external callers break."""
    import hashlib
    import hmac
    import json as jsonlib

    from unittest.mock import AsyncMock

    from aethon.gateway.webhooks import setup_webhooks

    app = _dashboard_app(token="secret")
    router = MagicMock()
    response = MagicMock()
    response.text = "Webhook yaniti"
    router.handle = AsyncMock(return_value=response)
    assert setup_webhooks(app, router, secret="hooksecret", host="127.0.0.1") is True

    client = TestClient(app)
    body = jsonlib.dumps({"text": "test"}).encode()
    sig = hmac.new(b"hooksecret", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhook/telegram",
        content=body,
        headers={"X-Aethon-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200  # no dashboard token supplied — HMAC suffices


# --- /ws/dashboard auth (gap closed: never previously tested) ---------------


def test_ws_dashboard_rejected_without_token():
    client = TestClient(_dashboard_app(token="secret"))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/dashboard"):
            pass
    assert exc.value.code == 1008


def test_ws_dashboard_accepts_query_token():
    client = TestClient(_dashboard_app(token="secret"))
    with client.websocket_connect("/ws/dashboard?token=secret") as ws:
        ws.send_json({"channel": "subscribe", "topics": ["messages"]})


def test_ws_dashboard_accepts_bearer_header():
    """token_ok gains Bearer support for WS — harmless superset, pinned here."""
    client = TestClient(_dashboard_app(token="secret"))
    with client.websocket_connect(
        "/ws/dashboard", headers={"Authorization": "Bearer secret"}
    ) as ws:
        ws.send_json({"channel": "subscribe", "topics": ["messages"]})


# --- /ws/dashboard Origin validation (S2) ------------------------------------


def test_ws_dashboard_rejects_cross_origin():
    """Cross-site Origin rejected pre-accept — even with the right token."""
    client = TestClient(_dashboard_app(token="secret"))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws/dashboard?token=secret", headers={"Origin": "http://evil.example"}
        ):
            pass
    assert exc.value.code == 1008


def test_ws_dashboard_allows_same_host_origin():
    client = TestClient(_dashboard_app(token="secret"))
    with client.websocket_connect(
        "/ws/dashboard?token=secret", headers={"Origin": "http://testserver"}
    ) as ws:
        ws.send_json({"channel": "subscribe", "topics": ["messages"]})


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
