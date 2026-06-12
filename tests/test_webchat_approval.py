"""Tests for WebChatAdapter.ask_approval (Phase 9A / S6 — WebChat answerable)."""

import asyncio
import json

import pytest
from unittest.mock import MagicMock

from aethon.config import AethonConfig
from aethon.channels.webchat import WebChatAdapter
from aethon.channels.base import ApprovalRequest


class _FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


def _adapter():
    return WebChatAdapter(AethonConfig(), MagicMock())


def _request(iid="i1"):
    return ApprovalRequest(
        interrupt_id=iid,
        tool="shell",
        parameters={"command": "ls"},
        message="'shell' calistirilmak isteniyor. Onayla?",
        session_id="webchat:local",
        recipient_id="local",
    )


@pytest.mark.asyncio
async def test_ask_approval_no_socket_fails_closed():
    adapter = _adapter()
    assert adapter._socket is None
    assert await adapter.ask_approval(_request()) is None


@pytest.mark.asyncio
async def test_ask_approval_approved():
    adapter = _adapter()
    adapter._socket = _FakeWS()
    task = asyncio.ensure_future(adapter.ask_approval(_request("i1")))
    await asyncio.sleep(0)  # let the card get sent + the future register
    # The approval card was pushed over the socket.
    frame = json.loads(adapter._socket.sent[0])
    assert frame["type"] == "approval" and frame["id"] == "i1"
    # The browser answers — resolve the pending future.
    assert adapter._maybe_resolve_approval(json.dumps({"type": "approval", "id": "i1", "decision": True})) is True
    assert await task is True


@pytest.mark.asyncio
async def test_ask_approval_denied():
    adapter = _adapter()
    adapter._socket = _FakeWS()
    task = asyncio.ensure_future(adapter.ask_approval(_request("i2")))
    await asyncio.sleep(0)
    adapter._maybe_resolve_approval(json.dumps({"type": "approval", "id": "i2", "decision": False}))
    assert await task is False


@pytest.mark.asyncio
async def test_disconnect_rejects_pending_to_deny():
    adapter = _adapter()
    adapter._socket = _FakeWS()
    task = asyncio.ensure_future(adapter.ask_approval(_request("i3")))
    await asyncio.sleep(0)
    adapter._reject_pending()  # simulates WebSocketDisconnect cleanup
    assert await task is False


def test_plain_text_not_intercepted():
    """Ordinary chat text — even JSON that isn't an approval frame — passes through."""
    adapter = _adapter()
    assert adapter._maybe_resolve_approval("merhaba") is False
    assert adapter._maybe_resolve_approval('{"foo": 1}') is False
    # A well-formed approval frame for an unknown id is still swallowed (not chat).
    assert adapter._maybe_resolve_approval('{"type":"approval","id":"zzz","decision":true}') is True


# Note: webchat-turn serialization is now the runtime's job (H1, per session_id);
# see tests/test_runtime.py::test_session_lock_serializes_same_session.


@pytest.mark.asyncio
async def test_new_connection_rejects_previous_pending():
    """A superseding connection denies the old tab's in-flight approval."""
    adapter = _adapter()
    adapter._socket = _FakeWS()
    task = asyncio.ensure_future(adapter.ask_approval(_request("i9")))
    await asyncio.sleep(0)
    adapter._reject_pending()  # what a new ws_chat accept triggers
    assert await task is False
