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

    with pytest.raises(ValueError, match="Discord token gerekli"):
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
