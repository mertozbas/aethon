"""Tests for channel base models."""

import pytest
from datetime import datetime

from aethon.channels.base import (
    MediaAttachment,
    InboundMessage,
    OutboundMessage,
    ChannelAdapter,
)


def test_inbound_message_creation():
    """InboundMessage creates with all fields."""
    msg = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="hello",
    )
    assert msg.channel == "cli"
    assert msg.sender_id == "local"
    assert msg.text == "hello"
    assert isinstance(msg.timestamp, datetime)
    assert msg.media == []
    assert msg.raw == {}


def test_outbound_message_creation():
    """OutboundMessage creates with all fields."""
    msg = OutboundMessage(
        channel="webchat",
        recipient_id="local",
        text="response",
    )
    assert msg.channel == "webchat"
    assert msg.recipient_id == "local"
    assert msg.text == "response"
    assert msg.raw == {}


def test_outbound_message_with_raw():
    """OutboundMessage carries channel-specific raw data."""
    msg = OutboundMessage(
        channel="telegram",
        recipient_id="123",
        text="response",
        raw={"chat_id": 456, "message_id": 789},
    )
    assert msg.raw["chat_id"] == 456
    assert msg.raw["message_id"] == 789


def test_media_attachment():
    """MediaAttachment creates correctly."""
    media = MediaAttachment(
        type="image",
        url="https://example.com/image.png",
        mime_type="image/png",
    )
    assert media.type == "image"
    assert media.url == "https://example.com/image.png"


def test_inbound_message_with_media():
    """InboundMessage with media attachments."""
    media = MediaAttachment(type="document", filename="test.pdf")
    msg = InboundMessage(
        channel="telegram",
        sender_id="123",
        sender_name="User",
        text="check this",
        media=[media],
    )
    assert len(msg.media) == 1
    assert msg.media[0].filename == "test.pdf"


def test_inbound_message_with_thread():
    """InboundMessage with thread_id."""
    msg = InboundMessage(
        channel="discord",
        sender_id="456",
        sender_name="User",
        text="thread reply",
        thread_id="thread-789",
    )
    assert msg.thread_id == "thread-789"


def test_channel_adapter_abc():
    """ChannelAdapter requires abstract methods."""
    with pytest.raises(TypeError):
        ChannelAdapter(config=None, router=None)


def test_channel_adapter_concrete():
    """Concrete ChannelAdapter implementation works."""

    class TestAdapter(ChannelAdapter):
        async def start(self):
            pass

        async def stop(self):
            pass

        async def send(self, message):
            pass

    adapter = TestAdapter(config=None, router=None)
    assert adapter is not None
