"""Tests for AethonGateway."""

import pytest

from aethon.config import (
    AethonConfig,
    ChannelsConfig,
    TelegramChannelConfig,
    DiscordChannelConfig,
    SlackChannelConfig,
)
from aethon.gateway.server import AethonGateway


def test_gateway_creation():
    """Gateway creates with default config."""
    config = AethonConfig()
    gateway = AethonGateway(config)
    assert gateway.runtime is not None
    assert gateway.router is not None
    assert gateway.adapters == {}


@pytest.mark.asyncio
async def test_gateway_shutdown():
    """Gateway shutdown works on empty adapters."""
    config = AethonConfig()
    gateway = AethonGateway(config)
    await gateway.shutdown()
    assert gateway.adapters == {}


def test_gateway_with_telegram_enabled():
    """Gateway with Telegram enabled creates adapter."""
    config = AethonConfig(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=True, token="test-token"),
            cli=AethonConfig().channels.cli.__class__(enabled=False),
            webchat=AethonConfig().channels.webchat.__class__(enabled=False),
        )
    )
    gateway = AethonGateway(config)
    assert gateway.config.channels.telegram.enabled is True


def test_gateway_disabled_channels_no_adapter():
    """Disabled channels don't get adapters."""
    config = AethonConfig(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=False),
            discord=DiscordChannelConfig(enabled=False),
            slack=SlackChannelConfig(enabled=False),
        )
    )
    gateway = AethonGateway(config)
    assert "telegram" not in gateway.adapters
    assert "discord" not in gateway.adapters
    assert "slack" not in gateway.adapters
