"""Tests for WhatsAppAdapter."""

from aethon.config import (
    AethonConfig, ChannelsConfig, SecurityConfig, WhatsAppChannelConfig,
)
from aethon.channels.base import ChannelAdapter, OutboundMessage
from aethon.channels.whatsapp import WhatsAppAdapter


def test_whatsapp_adapter_is_channel_adapter():
    """WhatsAppAdapter inherits from ChannelAdapter."""
    assert issubclass(WhatsAppAdapter, ChannelAdapter)


def test_whatsapp_adapter_creates_without_neonize():
    """Adapter construction does not require neonize (only start() does)."""
    adapter = WhatsAppAdapter(AethonConfig(), router=None)
    assert adapter.client is None


# --- _resolve_chat (proactive/outbound destination) tests ---


def _adapter(*, chat="", allowed=None):
    config = AethonConfig(
        channels=ChannelsConfig(
            whatsapp=WhatsAppChannelConfig(enabled=True, chat=chat),
        ),
        security=SecurityConfig(allowed_senders={"whatsapp": allowed} if allowed else {}),
    )
    return WhatsAppAdapter(config, router=None)


def _out(recipient_id="default", raw=None):
    return OutboundMessage(channel="whatsapp", recipient_id=recipient_id, text="hi", raw=raw or {})


def test_resolve_chat_prefers_inbound_raw():
    """Reactive replies use the inbound chat regardless of config."""
    adapter = _adapter(chat="905551112233")
    assert adapter._resolve_chat(_out(recipient_id="42", raw={"chat": "777"})) == "777"


def test_resolve_chat_explicit_recipient():
    adapter = _adapter()
    assert adapter._resolve_chat(_out(recipient_id="905551112233")) == "905551112233"


def test_resolve_chat_default_falls_back_to_config():
    """Proactive send with recipient 'default' must NOT build a 'default' JID —
    it resolves to the configured chat."""
    adapter = _adapter(chat="905551112233")
    assert adapter._resolve_chat(_out(recipient_id="default")) == "905551112233"


def test_resolve_chat_falls_back_to_allowed_senders():
    adapter = _adapter(allowed=["905559998877"])
    assert adapter._resolve_chat(_out(recipient_id="default")) == "905559998877"


def test_resolve_chat_none_when_nothing_configured():
    adapter = _adapter()
    assert adapter._resolve_chat(_out(recipient_id="default")) is None


def test_send_with_no_destination_skips_client():
    """Review fix: send() must skip cleanly instead of building a JID from
    'default'."""
    import asyncio
    from unittest.mock import MagicMock

    adapter = _adapter()
    adapter.client = MagicMock()
    asyncio.run(adapter.send(_out(recipient_id="default")))
    adapter.client.send_message.assert_not_called()
