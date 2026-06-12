"""Tests for MessageRouter."""

import pytest

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
    """Empty allowlist allows everyone on LOCAL channels (cli/webchat)."""
    msg = InboundMessage(
        channel="cli", sender_id="anyone", sender_name="Anyone", text="hello"
    )
    assert router_default._is_allowed(msg) is True


@pytest.mark.parametrize("channel", ["telegram", "discord", "slack", "whatsapp"])
def test_empty_allowlist_denies_network_channels(router_default, channel):
    """S5 (breaking): empty allowlist = reject ALL on network channels."""
    msg = InboundMessage(
        channel=channel, sender_id="anyone", sender_name="Anyone", text="hi"
    )
    assert router_default._is_allowed(msg) is False


@pytest.mark.parametrize("channel", ["cli", "webchat", "webhook:trigger", "webhook:github"])
def test_local_and_webhook_channels_open_with_empty_allowlist(router_default, channel):
    """The default-deny set must be EXACTLY the four bot channels: cli/webchat
    are local (webchat token-gated, S1) and webhook:* self-authenticates via
    HMAC (S3) with a fixed sender_id — denying them would brick those paths."""
    msg = InboundMessage(
        channel=channel, sender_id="webhook", sender_name="X", text="hi"
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
async def test_handle_rejected_replies_with_config_key(router_restricted):
    """S5: rejection is no longer a silent drop — the short reply names the
    exact config key and the sender id, so a locked-out owner can self-serve."""
    msg = InboundMessage(
        channel="telegram",
        sender_id="99999999",
        sender_name="Stranger",
        text="hi",
        raw={"chat_id": 42},
    )
    response = await router_restricted.handle(msg)
    assert response is not None
    assert "security.allowed_senders.telegram" in response.text
    assert "99999999" in response.text
    # raw must be copied — channel adapters route replies through it (telegram).
    assert response.raw == {"chat_id": 42}
    # The fixed reply must never contain agent output.
    assert "Echo:" not in response.text


@pytest.mark.asyncio
async def test_handle_propagates_raw(router_restricted):
    """Handle copies raw field from InboundMessage to OutboundMessage."""
    msg = InboundMessage(
        channel="telegram",
        sender_id="12345678",  # listed in router_restricted
        sender_name="User",
        text="hello",
        raw={"chat_id": 456, "message_id": 789},
    )
    response = await router_restricted.handle(msg)
    assert response is not None
    assert "Echo: hello" in response.text
    assert response.raw == {"chat_id": 456, "message_id": 789}
