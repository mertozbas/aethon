"""Tests for MessageRouter."""

import pytest
import asyncio

from aethon.config import AethonConfig, SecurityConfig
from aethon.channels.base import InboundMessage
from aethon.gateway.router import MessageRouter


class FakeRuntime:
    """Fake runtime that returns echo responses."""

    async def process(self, message, session_id):
        return f"Echo: {message.text} [session={session_id}]"


@pytest.fixture
def router_default():
    """Router with default config (empty allowlist)."""
    config = AethonConfig()
    runtime = FakeRuntime()
    return MessageRouter(config, runtime)


@pytest.fixture
def router_restricted():
    """Router with restricted senders."""
    config = AethonConfig(
        security=SecurityConfig(
            allowed_senders={
                "telegram": ["12345678"],
                "discord": ["98765432"],
            }
        )
    )
    runtime = FakeRuntime()
    return MessageRouter(config, runtime)


def test_allow_with_empty_allowlist(router_default):
    """Empty allowlist allows everyone."""
    msg = InboundMessage(
        channel="cli", sender_id="anyone", sender_name="Anyone", text="hello"
    )
    assert router_default._is_allowed(msg) is True


def test_allow_listed_sender(router_restricted):
    """Listed sender is allowed."""
    msg = InboundMessage(
        channel="telegram", sender_id="12345678", sender_name="User", text="hi"
    )
    assert router_restricted._is_allowed(msg) is True


def test_reject_unlisted_sender(router_restricted):
    """Unlisted sender is rejected."""
    msg = InboundMessage(
        channel="telegram", sender_id="99999999", sender_name="Stranger", text="hi"
    )
    assert router_restricted._is_allowed(msg) is False


def test_allow_unconfigured_channel(router_restricted):
    """Channel without allowlist allows everyone."""
    msg = InboundMessage(
        channel="cli", sender_id="anyone", sender_name="Anyone", text="hi"
    )
    assert router_restricted._is_allowed(msg) is True


def test_session_id_format(router_default):
    """Session ID uses channel:sender_id format."""
    msg = InboundMessage(
        channel="cli", sender_id="local", sender_name="User", text="hi"
    )
    session_id = router_default._resolve_session(msg)
    assert session_id == "cli:local"


def test_session_id_with_thread(router_default):
    """Thread ID overrides sender_id in session."""
    msg = InboundMessage(
        channel="discord",
        sender_id="user123",
        sender_name="User",
        text="hi",
        thread_id="thread-456",
    )
    session_id = router_default._resolve_session(msg)
    assert session_id == "discord:thread-456"


@pytest.mark.asyncio
async def test_handle_allowed(router_default):
    """Handle returns response for allowed message."""
    msg = InboundMessage(
        channel="cli", sender_id="local", sender_name="User", text="hello"
    )
    response = await router_default.handle(msg)
    assert response is not None
    assert "Echo: hello" in response.text
    assert response.channel == "cli"
    assert response.recipient_id == "local"


@pytest.mark.asyncio
async def test_handle_rejected(router_restricted):
    """Handle returns None for rejected message."""
    msg = InboundMessage(
        channel="telegram", sender_id="99999999", sender_name="Stranger", text="hi"
    )
    response = await router_restricted.handle(msg)
    assert response is None


@pytest.mark.asyncio
async def test_handle_propagates_raw(router_default):
    """Handle copies raw field from InboundMessage to OutboundMessage."""
    msg = InboundMessage(
        channel="telegram",
        sender_id="123",
        sender_name="User",
        text="hello",
        raw={"chat_id": 456, "message_id": 789},
    )
    response = await router_default.handle(msg)
    assert response is not None
    assert response.raw == {"chat_id": 456, "message_id": 789}
