"""Tests for WebChatAdapter."""

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from aethon.config import AethonConfig
from aethon.channels.webchat import WebChatAdapter


class FakeRouter:
    """Fake router for testing."""

    async def handle(self, message):
        from aethon.channels.base import OutboundMessage
        return OutboundMessage(
            channel="webchat",
            recipient_id="local",
            text=f"Echo: {message.text}",
        )


def _app(token: str = ""):
    """WebChatAdapter app with an optional shared auth token."""
    config = AethonConfig()
    config.dashboard.auth_token = token
    return WebChatAdapter(config, FakeRouter()).app


@pytest.fixture
def webchat_app():
    """WebChatAdapter's FastAPI app (no auth token — default config)."""
    return _app()


def test_index_returns_html(webchat_app):
    """GET / returns HTML page."""
    client = TestClient(webchat_app)
    response = client.get("/")
    assert response.status_code == 200
    assert "AETHON" in response.text
    assert "text/html" in response.headers["content-type"]


def test_status_endpoint(webchat_app):
    """GET /api/status returns JSON."""
    from aethon import __version__

    client = TestClient(webchat_app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["version"] == __version__


def test_health_endpoint(webchat_app):
    """GET /health is a lightweight, always-open liveness probe."""
    client = TestClient(webchat_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_websocket_chat(webchat_app):
    """WebSocket /ws/chat sends and receives messages (no token configured = open)."""
    client = TestClient(webchat_app)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("hello")
        response = ws.receive_text()
        assert "Echo: hello" in response


# --- /ws/chat auth (Phase 9A / S1) ------------------------------------------


def test_ws_chat_rejected_without_token():
    """Tokened server rejects an upgrade with no token BEFORE accept (1008)."""
    client = TestClient(_app(token="secret"))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/chat"):
            pass
    assert exc.value.code == 1008


def test_ws_chat_rejected_with_wrong_token():
    client = TestClient(_app(token="secret"))
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/chat?token=nope"):
            pass
    assert exc.value.code == 1008


def test_ws_chat_accepts_query_token():
    client = TestClient(_app(token="secret"))
    with client.websocket_connect("/ws/chat?token=secret") as ws:
        ws.send_text("merhaba")
        assert "Echo: merhaba" in ws.receive_text()


def test_ws_chat_accepts_bearer_header():
    client = TestClient(_app(token="secret"))
    with client.websocket_connect(
        "/ws/chat", headers={"Authorization": "Bearer secret"}
    ) as ws:
        ws.send_text("hi")
        assert "Echo: hi" in ws.receive_text()


def test_ws_chat_accepts_cookie():
    """The aethon_dash cookie (set by /dashboard?token=...) also opens the chat."""
    client = TestClient(_app(token="secret"))
    client.cookies.set("aethon_dash", "secret")
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("hi")
        assert "Echo: hi" in ws.receive_text()


# --- Deny-by-default HTTP gate on the webchat app (Phase 9A / S1) ------------


def test_chat_page_public_with_token():
    """The chat page itself stays public — only its WebSocket is gated."""
    client = TestClient(_app(token="secret"))
    assert client.get("/").status_code == 200


def test_health_public_with_token():
    client = TestClient(_app(token="secret"))
    assert client.get("/health").status_code == 200


def test_status_gated_with_token():
    """/api/status is protected under deny-by-default (it leaks the version)."""
    client = TestClient(_app(token="secret"))
    assert client.get("/api/status").status_code == 401
    ok = client.get("/api/status", headers={"Authorization": "Bearer secret"})
    assert ok.status_code == 200


def test_chat_html_ws_url_is_proto_aware():
    """The inline JS must pick wss: under https (TLS reverse proxy)."""
    client = TestClient(_app())
    body = client.get("/").text
    assert "'wss:'" in body and "'ws:'" in body
    assert "sessionStorage" in body  # token prompt wiring present
