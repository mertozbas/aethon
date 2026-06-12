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

    # Keep the exposed-bind config but never bind a real socket. Mark the noop
    # as fire-and-return so the supervisor doesn't treat its clean return as an
    # unexpected stop and restart it (the new H3 behavior).
    monkeypatch.setattr(WebChatAdapter, "start", _noop_start)
    monkeypatch.setattr(WebChatAdapter, "blocking", False)
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


@pytest.mark.asyncio
async def test_gateway_logs_error_for_enabled_bot_with_empty_allowlist(
    monkeypatch, caplog
):
    """S5: bot enabled + empty allowlist -> boot ERROR naming the config key
    (the bot still starts; default-deny makes it safe but useless)."""
    import logging

    from aethon.channels.webchat import WebChatAdapter

    async def _noop_start(self):
        return None

    monkeypatch.setattr(WebChatAdapter, "start", _noop_start)
    monkeypatch.setattr(WebChatAdapter, "blocking", False)
    config = _config()
    config.channels.cli.enabled = False
    config.channels.telegram.enabled = True  # no allowlist configured
    config.scheduler.enabled = False
    config.dashboard.enabled = False
    config.webhook.enabled = False
    gateway = AethonGateway(config)
    with caplog.at_level(logging.ERROR, logger="aethon.gateway"):
        await gateway.start()
    assert any(
        "security.allowed_senders.telegram" in r.message for r in caplog.records
    )


@pytest.mark.asyncio
async def test_supervisor_restarts_then_degrades_one_channel():
    """A crashing channel is retried with backoff, then degraded — the gateway
    keeps running (H3)."""
    gateway = AethonGateway(_config())
    gateway._shutdown_event = __import__("asyncio").Event()
    gateway._degraded_channels = []
    gateway._MAX_CHANNEL_RETRIES = 2  # speed up the test

    calls = {"n": 0}

    class _CrashingAdapter:
        async def start(self):
            calls["n"] += 1
            raise RuntimeError("boom")

    # Patch sleep so backoff is instant.
    import aethon.gateway.server as srv

    async def _instant_sleep(_):
        return None

    orig_sleep = srv.asyncio.sleep
    srv.asyncio.sleep = _instant_sleep
    try:
        await gateway._supervise("telegram", _CrashingAdapter())
    finally:
        srv.asyncio.sleep = orig_sleep

    assert "telegram" in gateway._degraded_channels
    assert calls["n"] == 3  # initial + 2 retries, then degrade


@pytest.mark.asyncio
async def test_supervisor_cli_clean_exit_triggers_shutdown():
    """The interactive CLI returning cleanly brings the gateway down (H3)."""
    import asyncio as _asyncio

    gateway = AethonGateway(_config())
    gateway._shutdown_event = _asyncio.Event()
    gateway._degraded_channels = []

    class _CleanCLI:
        async def start(self):
            return  # user typed 'exit'

    await gateway._supervise("cli", _CleanCLI())
    assert gateway._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_supervisor_blocking_bot_clean_exit_restarts_not_shutdown():
    """A blocking network bot returning unexpectedly is RESTARTED under the retry
    budget (a lone bot's transient stop must not tear the gateway down), and only
    degrades after the budget — it never sets the shutdown event (H3 review)."""
    import asyncio as _asyncio

    gateway = AethonGateway(_config())
    gateway._shutdown_event = _asyncio.Event()
    gateway._degraded_channels = []
    gateway._MAX_CHANNEL_RETRIES = 2  # speed up the test

    calls = {"n": 0}

    class _CleanBot:  # blocking=True by default → return is "unexpected"
        async def start(self):
            calls["n"] += 1
            return

    import aethon.gateway.server as srv

    async def _instant_sleep(_):
        return None

    orig_sleep = srv.asyncio.sleep
    srv.asyncio.sleep = _instant_sleep
    try:
        await gateway._supervise("telegram", _CleanBot())
    finally:
        srv.asyncio.sleep = orig_sleep

    assert calls["n"] == 3  # initial + 2 restarts, then degrade
    assert "telegram" in gateway._degraded_channels
    assert not gateway._shutdown_event.is_set()  # never brought the gateway down


@pytest.mark.asyncio
async def test_supervisor_fire_and_return_adapter_exits_cleanly():
    """A non-blocking adapter (blocking=False, e.g. WhatsApp) handing off to a
    background client returns once — no restart, no degrade, no shutdown."""
    import asyncio as _asyncio

    gateway = AethonGateway(_config())
    gateway._shutdown_event = _asyncio.Event()
    gateway._degraded_channels = []

    calls = {"n": 0}

    class _BackgroundBot:
        blocking = False

        async def start(self):
            calls["n"] += 1
            return  # handed off to a background client

    await gateway._supervise("whatsapp", _BackgroundBot())

    assert calls["n"] == 1  # not restarted
    assert "whatsapp" not in gateway._degraded_channels
    assert not gateway._shutdown_event.is_set()


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
