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
