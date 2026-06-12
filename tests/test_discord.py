"""Tests for DiscordAdapter."""

import pytest

from aethon.config import AethonConfig, DiscordChannelConfig, ChannelsConfig


def test_discord_adapter_requires_token():
    """DiscordAdapter raises ValueError without token."""
    config = AethonConfig(
        channels=ChannelsConfig(
            discord=DiscordChannelConfig(enabled=True, token=""),
        )
    )
    from aethon.channels.discord_adapter import DiscordAdapter

    with pytest.raises(ValueError, match="Discord token required"):
        DiscordAdapter(config, router=None)


def test_discord_adapter_creates_with_token():
    """DiscordAdapter creates successfully with token."""
    config = AethonConfig(
        channels=ChannelsConfig(
            discord=DiscordChannelConfig(enabled=True, token="test-discord-token"),
        )
    )
    from aethon.channels.discord_adapter import DiscordAdapter

    adapter = DiscordAdapter(config, router=None)
    assert adapter.token == "test-discord-token"
    assert adapter.client is None


def test_discord_adapter_is_channel_adapter():
    """DiscordAdapter inherits from ChannelAdapter."""
    from aethon.channels.discord_adapter import DiscordAdapter
    from aethon.channels.base import ChannelAdapter

    assert issubclass(DiscordAdapter, ChannelAdapter)


# --- _resolve_channel_id (proactive/outbound destination) tests ---


def _adapter(*, channel_id="", allowed=None):
    from aethon.config import SecurityConfig
    from aethon.channels.discord_adapter import DiscordAdapter

    config = AethonConfig(
        channels=ChannelsConfig(
            discord=DiscordChannelConfig(
                enabled=True, token="test-token", channel_id=channel_id
            ),
        ),
        security=SecurityConfig(allowed_senders={"discord": allowed} if allowed else {}),
    )
    return DiscordAdapter(config, router=None)


def _out(recipient_id="default", raw=None):
    from aethon.channels.base import OutboundMessage

    return OutboundMessage(channel="discord", recipient_id=recipient_id, text="hi", raw=raw or {})


def test_resolve_channel_id_prefers_inbound_raw():
    """Reactive replies use the inbound channel id regardless of config."""
    adapter = _adapter(channel_id="999")
    assert adapter._resolve_channel_id(_out(recipient_id="42", raw={"channel_id": 7})) == 7


def test_resolve_channel_id_numeric_recipient():
    adapter = _adapter()
    assert adapter._resolve_channel_id(_out(recipient_id="123456")) == 123456


def test_resolve_channel_id_default_falls_back_to_config():
    """Proactive send with recipient 'default' must NOT crash (old int('default')) — it
    resolves to the configured channel_id."""
    adapter = _adapter(channel_id="555")
    assert adapter._resolve_channel_id(_out(recipient_id="default")) == 555


def test_resolve_channel_id_falls_back_to_allowed_senders():
    adapter = _adapter(allowed=["6875048694"])
    assert adapter._resolve_channel_id(_out(recipient_id="default")) == 6875048694


def test_resolve_channel_id_skips_non_numeric_allowed_senders():
    adapter = _adapter(allowed=["not-a-number", "777"])
    assert adapter._resolve_channel_id(_out(recipient_id="default")) == 777


def test_resolve_channel_id_none_when_nothing_configured():
    adapter = _adapter()
    assert adapter._resolve_channel_id(_out(recipient_id="default")) is None


# --- review fixes: explicit recipients must not silently redirect ---


def test_explicit_non_numeric_recipient_returns_none():
    """Review fix: '#general' must NOT silently fall back to the configured
    default (wrong-destination delivery reported as success)."""
    adapter = _adapter(channel_id="555")
    assert adapter._resolve_channel_id(_out(recipient_id="#general")) is None


def test_malformed_numeric_recipient_returns_none():
    """'--123' passes isdigit-after-lstrip but crashes int() — coercion must
    be exception-safe."""
    adapter = _adapter()
    assert adapter._resolve_channel_id(_out(recipient_id="--123")) is None


def test_non_numeric_raw_channel_id_returns_none():
    adapter = _adapter()
    assert adapter._resolve_channel_id(_out(raw={"channel_id": "bozuk"})) is None


# --- review fixes: send()-level coverage (the original R2 bug lived here) ---


def test_send_with_no_destination_skips_client(tmp_path):
    """send() with nothing resolvable must not touch the client (the old
    int('default') crash lived exactly here)."""
    import asyncio
    from unittest.mock import MagicMock

    adapter = _adapter()
    adapter.client = MagicMock()
    asyncio.run(adapter.send(_out(recipient_id="default")))
    adapter.client.get_channel.assert_not_called()


def test_send_chunks_long_messages():
    """>2000 chars must be split into 2000-char chunks."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    adapter = _adapter(channel_id="555")
    channel = MagicMock()
    channel.send = AsyncMock()
    adapter.client = MagicMock()
    adapter.client.get_channel.return_value = channel

    msg = _out(recipient_id="555")
    msg.text = "x" * 4500
    asyncio.run(adapter.send(msg))
    assert channel.send.await_count == 3


def test_discord_typing_context_uses_channel_typing():
    """H5: typing_context returns the resolved channel's typing() manager."""
    from unittest.mock import MagicMock
    from aethon.channels.discord_adapter import DiscordAdapter
    from aethon.channels.base import InboundMessage

    config = AethonConfig(
        channels=ChannelsConfig(discord=DiscordChannelConfig(enabled=True, token="t")),
    )
    adapter = DiscordAdapter(config, router=None)
    sentinel = object()
    channel = MagicMock()
    channel.typing = MagicMock(return_value=sentinel)
    adapter.client = MagicMock()
    adapter.client.get_channel = MagicMock(return_value=channel)

    inbound = InboundMessage(
        channel="discord", sender_id="1", sender_name="U", text="hi",
        raw={"channel_id": 99},
    )
    assert adapter.typing_context(inbound) is sentinel
    adapter.client.get_channel.assert_called_once_with(99)


def test_discord_typing_noop_without_channel():
    import contextlib
    from unittest.mock import MagicMock
    from aethon.channels.discord_adapter import DiscordAdapter
    from aethon.channels.base import InboundMessage

    config = AethonConfig(
        channels=ChannelsConfig(discord=DiscordChannelConfig(enabled=True, token="t")),
    )
    adapter = DiscordAdapter(config, router=None)
    adapter.client = MagicMock()
    adapter.client.get_channel = MagicMock(return_value=None)
    inbound = InboundMessage(channel="discord", sender_id="1", sender_name="U", text="hi")
    assert isinstance(adapter.typing_context(inbound), contextlib.nullcontext)
