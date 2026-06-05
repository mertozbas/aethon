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
