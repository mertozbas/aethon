"""Tests for webhook endpoints."""

import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aethon.gateway.webhooks import setup_webhooks


@pytest.fixture
def mock_router():
    router = MagicMock()
    response = MagicMock()
    response.text = "Webhook yaniti"
    router.handle = AsyncMock(return_value=response)
    return router


@pytest.fixture
def app_no_secret(mock_router):
    """FastAPI app with webhooks (no secret)."""
    app = FastAPI()
    setup_webhooks(app, mock_router, secret="")
    return app


@pytest.fixture
def app_with_secret(mock_router):
    """FastAPI app with webhooks (secret enabled)."""
    app = FastAPI()
    setup_webhooks(app, mock_router, secret="test-secret")
    return app


def test_webhook_channel_success(app_no_secret):
    """POST /webhook/{channel} returns response."""
    client = TestClient(app_no_secret)
    resp = client.post(
        "/webhook/telegram",
        json={"text": "Merhaba"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["response"] == "Webhook yaniti"


def test_webhook_trigger_success(app_no_secret):
    """POST /webhook/trigger returns response."""
    client = TestClient(app_no_secret)
    resp = client.post(
        "/webhook/trigger",
        json={"text": "Merhaba"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_trigger_with_sop(app_no_secret, mock_router):
    """POST /webhook/trigger with sop_name prepends /."""
    client = TestClient(app_no_secret)
    client.post(
        "/webhook/trigger",
        json={"sop_name": "morning-brief", "text": "bugun"},
    )
    call_args = mock_router.handle.call_args
    inbound = call_args[0][0]
    assert inbound.text == "/morning-brief bugun"


def test_webhook_no_secret_loopback_allows_any_and_warns(mock_router, caplog):
    """Empty secret on a LOOPBACK bind keeps working (local dev) but warns (S3)."""
    import logging

    app = FastAPI()
    with caplog.at_level(logging.WARNING, logger="aethon.webhooks"):
        registered = setup_webhooks(app, mock_router, secret="", host="127.0.0.1")
    assert registered is True
    assert any("UNAUTHENTICATED" in r.message for r in caplog.records)
    client = TestClient(app)
    resp = client.post("/webhook/telegram", json={"text": "test"})
    assert resp.status_code == 200


def test_webhook_no_secret_nonloopback_refuses_registration(mock_router, caplog):
    """Empty secret on a non-loopback bind: routes NOT registered, ERROR log (S3)."""
    import logging

    app = FastAPI()
    with caplog.at_level(logging.ERROR, logger="aethon.webhooks"):
        registered = setup_webhooks(app, mock_router, secret="", host="0.0.0.0")
    assert registered is False
    assert any("webhook.secret" in r.message for r in caplog.records)
    client = TestClient(app)
    assert client.post("/webhook/trigger", json={"text": "x"}).status_code == 404
    assert client.post("/webhook/telegram", json={"text": "x"}).status_code == 404


def test_webhook_secret_nonloopback_registers(mock_router):
    """A secret keeps webhooks available on an exposed bind (HMAC verified)."""
    app = FastAPI()
    assert setup_webhooks(app, mock_router, secret="test-secret", host="0.0.0.0") is True
    client = TestClient(app)
    body = json.dumps({"text": "test"}).encode()
    sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhook/telegram",
        content=body,
        headers={"X-Aethon-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200


def test_webhook_trigger_route_order_preserved(app_no_secret, mock_router):
    """/webhook/trigger must match BEFORE /webhook/{channel} (registration order)."""
    client = TestClient(app_no_secret)
    client.post("/webhook/trigger", json={"text": "x"})
    inbound = mock_router.handle.call_args[0][0]
    assert inbound.channel == "webhook:trigger"


def test_webhook_invalid_secret(app_with_secret):
    """Invalid secret returns 403."""
    client = TestClient(app_with_secret)
    resp = client.post(
        "/webhook/telegram",
        json={"text": "test"},
        headers={"X-Aethon-Signature": "invalid"},
    )
    assert resp.status_code == 403


def test_webhook_valid_secret(app_with_secret):
    """Valid HMAC signature passes."""
    client = TestClient(app_with_secret)
    body = json.dumps({"text": "test"}).encode()
    sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhook/telegram",
        content=body,
        headers={
            "X-Aethon-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200


def test_webhook_channel_in_inbound(app_no_secret, mock_router):
    """Webhook sets channel to webhook:{channel}."""
    client = TestClient(app_no_secret)
    client.post("/webhook/discord", json={"text": "test"})
    call_args = mock_router.handle.call_args
    inbound = call_args[0][0]
    assert inbound.channel == "webhook:discord"
    assert inbound.sender_id == "webhook"
