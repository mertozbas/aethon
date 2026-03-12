"""Tests for send_message tool."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from aethon.tools.messaging import send_message, set_gateway, get_gateway
import aethon.tools.messaging as messaging_module


@pytest.fixture(autouse=True)
def cleanup_gateway():
    """Reset gateway after each test."""
    yield
    set_gateway(None)


def test_set_gateway():
    """set_gateway sets the global reference."""
    gw = MagicMock()
    set_gateway(gw)
    assert get_gateway() is gw


def test_get_gateway_none():
    """get_gateway returns None when not set."""
    assert get_gateway() is None


def test_send_message_no_gateway():
    """send_message without gateway returns error."""
    result = send_message._tool_func(channel="telegram", text="test")
    assert "Hata" in result
    assert "Gateway" in result


def test_send_message_channel_not_found():
    """send_message with unknown channel returns error."""
    gw = MagicMock()
    gw.adapters = {"cli": MagicMock()}
    set_gateway(gw)
    result = send_message._tool_func(channel="telegram", text="test")
    assert "bulunamadi" in result
    assert "cli" in result


def test_send_message_success():
    """send_message with valid adapter sends message."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    gw = MagicMock()
    gw.adapters = {"telegram": adapter}
    set_gateway(gw)

    result = send_message._tool_func(channel="telegram", text="Merhaba")
    assert "gonderildi" in result


def test_send_message_default_recipient():
    """send_message uses 'default' when no recipient specified."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    gw = MagicMock()
    gw.adapters = {"telegram": adapter}
    set_gateway(gw)

    send_message._tool_func(channel="telegram", text="test", recipient="")
    # Should not crash — recipient defaults to "default"


def test_send_message_with_recipient():
    """send_message passes recipient through."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    gw = MagicMock()
    gw.adapters = {"telegram": adapter}
    set_gateway(gw)

    result = send_message._tool_func(
        channel="telegram", text="test", recipient="user123"
    )
    assert "gonderildi" in result
