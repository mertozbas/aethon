"""Tests for AethonGateway."""

import pytest

from aethon.config import (
    AethonConfig,
    ModelConfig,
    ChannelsConfig,
    TelegramChannelConfig,
    DiscordChannelConfig,
    SlackChannelConfig,
)
from aethon.gateway.server import AethonGateway


def _config(**kwargs) -> AethonConfig:
    """AethonConfig using the offline `echo` provider, so the gateway/runtime builds
    without requiring an optional model SDK (the default `openai` needs the openai SDK)."""
    cfg = AethonConfig(**kwargs)
    cfg.model = ModelConfig(provider="echo", model_id="gpt-4o")
    return cfg


def test_gateway_creation():
    """Gateway creates with default config."""
    gateway = AethonGateway(_config())
    assert gateway.runtime is not None
    assert gateway.router is not None
    assert gateway.adapters == {}


@pytest.mark.asyncio
async def test_gateway_shutdown():
    """Gateway shutdown works on empty adapters."""
    gateway = AethonGateway(_config())
    await gateway.shutdown()
    assert gateway.adapters == {}


def test_gateway_with_telegram_enabled():
    """Gateway with Telegram enabled creates adapter."""
    config = _config(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=True, token="test-token"),
            cli=AethonConfig().channels.cli.__class__(enabled=False),
            webchat=AethonConfig().channels.webchat.__class__(enabled=False),
        )
    )
    gateway = AethonGateway(config)
    assert gateway.config.channels.telegram.enabled is True


@pytest.mark.asyncio
async def test_gateway_refuses_nonloopback_bind_without_token():
    """Non-loopback bind + empty dashboard.auth_token must refuse to start (S4)."""
    config = _config()
    config.channels.webchat.host = "0.0.0.0"
    gateway = AethonGateway(config)
    with pytest.raises(RuntimeError, match="dashboard.auth_token"):
        await gateway.start()
    # Refusal happens before any adapter/task side effect.
    assert gateway.adapters == {}


@pytest.mark.asyncio
async def test_gateway_insecure_bind_skips_refusal(monkeypatch, caplog):
    """--insecure-bind continues past the S4 gate (warns instead of raising)."""
    import logging

    from aethon.channels.webchat import WebChatAdapter

    async def _noop_start(self):
        return None

    # Keep the exposed-bind config but never bind a real socket.
    monkeypatch.setattr(WebChatAdapter, "start", _noop_start)
    config = _config()
    config.channels.webchat.host = "0.0.0.0"
    config.channels.cli.enabled = False
    config.scheduler.enabled = False
    config.dashboard.enabled = False
    config.webhook.enabled = False
    gateway = AethonGateway(config, insecure_bind=True)
    with caplog.at_level(logging.WARNING, logger="aethon.gateway"):
        await gateway.start()
    assert any("--insecure-bind" in r.message for r in caplog.records)


def test_gateway_disabled_channels_no_adapter():
    """Disabled channels don't get adapters."""
    config = _config(
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
