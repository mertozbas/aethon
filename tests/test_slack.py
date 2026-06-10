"""Tests for SlackAdapter."""

import pytest

from aethon.config import AethonConfig, SlackChannelConfig, ChannelsConfig


def test_slack_adapter_requires_tokens():
    """SlackAdapter raises ValueError without tokens."""
    config = AethonConfig(
        channels=ChannelsConfig(
            slack=SlackChannelConfig(enabled=True, bot_token="", app_token=""),
        )
    )
    from aethon.channels.slack_adapter import SlackAdapter

    with pytest.raises(ValueError, match="bot_token and app_token required"):
        SlackAdapter(config, router=None)


def test_slack_adapter_requires_app_token():
    """SlackAdapter raises ValueError without app_token."""
    config = AethonConfig(
        channels=ChannelsConfig(
            slack=SlackChannelConfig(
                enabled=True, bot_token="xoxb-test", app_token=""
            ),
        )
    )
    from aethon.channels.slack_adapter import SlackAdapter

    with pytest.raises(ValueError, match="bot_token and app_token required"):
        SlackAdapter(config, router=None)


def test_slack_adapter_creates_with_tokens():
    """SlackAdapter creates successfully with both tokens."""
    config = AethonConfig(
        channels=ChannelsConfig(
            slack=SlackChannelConfig(
                enabled=True, bot_token="xoxb-test", app_token="xapp-test"
            ),
        )
    )
    from aethon.channels.slack_adapter import SlackAdapter

    adapter = SlackAdapter(config, router=None)
    assert adapter.bot_token == "xoxb-test"
    assert adapter.app_token == "xapp-test"
    assert adapter.app is None


def test_slack_adapter_is_channel_adapter():
    """SlackAdapter inherits from ChannelAdapter."""
    from aethon.channels.slack_adapter import SlackAdapter
    from aethon.channels.base import ChannelAdapter

    assert issubclass(SlackAdapter, ChannelAdapter)


# --- _resolve_channel (proactive/outbound destination) tests ---


def _adapter(*, channel="", allowed=None):
    from aethon.config import SecurityConfig
    from aethon.channels.slack_adapter import SlackAdapter

    config = AethonConfig(
        channels=ChannelsConfig(
            slack=SlackChannelConfig(
                enabled=True, bot_token="xoxb-test", app_token="xapp-test",
                channel=channel,
            ),
        ),
        security=SecurityConfig(allowed_senders={"slack": allowed} if allowed else {}),
    )
    return SlackAdapter(config, router=None)


def _out(recipient_id="default", raw=None):
    from aethon.channels.base import OutboundMessage

    return OutboundMessage(channel="slack", recipient_id=recipient_id, text="hi", raw=raw or {})


def test_resolve_channel_prefers_inbound_raw():
    """Reactive replies use the inbound channel regardless of config."""
    adapter = _adapter(channel="C999")
    assert adapter._resolve_channel(_out(recipient_id="C42", raw={"channel": "C7"})) == "C7"


def test_resolve_channel_explicit_recipient():
    adapter = _adapter()
    assert adapter._resolve_channel(_out(recipient_id="C123456")) == "C123456"


def test_resolve_channel_default_falls_back_to_config():
    """Proactive send with recipient 'default' must NOT reach the API as a
    channel name — it resolves to the configured channel."""
    adapter = _adapter(channel="C555")
    assert adapter._resolve_channel(_out(recipient_id="default")) == "C555"


def test_resolve_channel_falls_back_to_allowed_senders():
    adapter = _adapter(allowed=["U777"])
    assert adapter._resolve_channel(_out(recipient_id="default")) == "U777"


def test_resolve_channel_none_when_nothing_configured():
    adapter = _adapter()
    assert adapter._resolve_channel(_out(recipient_id="default")) is None
