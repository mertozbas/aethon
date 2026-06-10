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
    assert "Error" in result
    assert "Gateway" in result


def test_send_message_channel_not_found():
    """send_message with unknown channel returns error."""
    gw = MagicMock()
    gw.adapters = {"cli": MagicMock()}
    set_gateway(gw)
    result = send_message._tool_func(channel="telegram", text="test")
    assert "not found" in result
    assert "cli" in result


def _mock_gateway(adapter, channel="telegram", loop=None):
    gw = MagicMock()
    gw.adapters = {channel: adapter}
    gw.loop = loop
    return gw


def test_send_message_success():
    """send_message with valid adapter sends message."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    set_gateway(_mock_gateway(adapter))

    result = send_message._tool_func(channel="telegram", text="Merhaba")
    assert "sent" in result
    assert adapter.send.await_count == 1


def test_send_message_default_recipient():
    """send_message uses 'default' when no recipient specified."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    set_gateway(_mock_gateway(adapter))

    send_message._tool_func(channel="telegram", text="test", recipient="")
    # Should not crash — recipient defaults to "default"


def test_send_message_with_recipient():
    """send_message passes recipient through."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    set_gateway(_mock_gateway(adapter))

    result = send_message._tool_func(
        channel="telegram", text="test", recipient="user123"
    )
    assert "sent" in result


# --- R3 regressions: the tool must report the real outcome ---


def test_send_message_unresolvable_recipient_is_an_error():
    """A channel with no deliverable recipient returns an explicit error
    before dispatch, instead of 'sent' + a silently dropped message."""
    adapter = MagicMock()
    adapter.send = AsyncMock()
    adapter.resolve_recipient = lambda outbound: None
    set_gateway(_mock_gateway(adapter))

    result = send_message._tool_func(channel="telegram", text="test")
    assert "Error" in result
    assert "recipient" in result
    assert adapter.send.await_count == 0


def test_send_message_failure_returns_error():
    """A crashed send returns an error string, not success."""
    adapter = MagicMock()
    adapter.send = AsyncMock(side_effect=RuntimeError("boom"))
    set_gateway(_mock_gateway(adapter))

    result = send_message._tool_func(channel="telegram", text="test")
    assert "Error" in result
    assert "boom" in result


def test_send_message_runs_on_gateway_loop_and_reports_failure():
    """Worker-thread path: the send runs on the gateway loop and a crash
    there is reported as an error (the old fire-and-forget said 'sent')."""
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        async def boom(outbound):
            raise RuntimeError("kanal patladi")

        adapter = MagicMock()
        adapter.send = boom
        adapter.resolve_recipient = lambda outbound: "42"
        set_gateway(_mock_gateway(adapter, loop=loop))

        result = send_message._tool_func(channel="telegram", text="test")
        assert "Error" in result
        assert "kanal patladi" in result
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


def test_send_message_runs_on_gateway_loop_success():
    """Worker-thread path waits for completion before reporting success."""
    import asyncio
    import threading

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        sent = []

        async def record(outbound):
            sent.append(outbound.text)

        adapter = MagicMock()
        adapter.send = record
        adapter.resolve_recipient = lambda outbound: "42"
        set_gateway(_mock_gateway(adapter, loop=loop))

        result = send_message._tool_func(channel="telegram", text="Merhaba")
        assert "sent" in result
        assert sent == ["Merhaba"]
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


def test_send_message_in_loop_reports_queued_not_sent():
    """On the event-loop thread the tool cannot block; it must say 'queued'
    (honest wording) and actually schedule the send."""
    import asyncio

    async def main():
        started = asyncio.Event()

        async def mark(outbound):
            started.set()

        adapter = MagicMock()
        adapter.send = mark
        adapter.resolve_recipient = lambda outbound: "42"
        set_gateway(_mock_gateway(adapter, loop=asyncio.get_running_loop()))

        result = send_message._tool_func(channel="telegram", text="test")
        assert "queued" in result
        assert "sent via" not in result
        await asyncio.wait_for(started.wait(), timeout=5)

    asyncio.run(main())
