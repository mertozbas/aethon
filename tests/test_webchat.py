"""Tests for WebChatAdapter."""

import pytest
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


@pytest.fixture
def webchat_app():
    """WebChatAdapter's FastAPI app."""
    config = AethonConfig()
    router = FakeRouter()
    adapter = WebChatAdapter(config, router)
    return adapter.app


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
    """WebSocket /ws/chat sends and receives messages."""
    client = TestClient(webchat_app)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_text("hello")
        response = ws.receive_text()
        assert "Echo: hello" in response
