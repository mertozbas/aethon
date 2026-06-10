"""Tests for DashboardEventBus."""

import asyncio

from aethon.ui.event_bus import DashboardEventBus


def test_subscribe_creates_queue():
    """subscribe() returns an asyncio.Queue and adds to subscribers."""
    bus = DashboardEventBus()
    q = bus.subscribe()
    assert isinstance(q, asyncio.Queue)
    assert bus.subscriber_count == 1


def test_unsubscribe_removes_queue():
    """unsubscribe() removes the queue from subscribers."""
    bus = DashboardEventBus()
    q = bus.subscribe()
    assert bus.subscriber_count == 1
    bus.unsubscribe(q)
    assert bus.subscriber_count == 0


def test_unsubscribe_nonexistent_is_safe():
    """unsubscribe() with unknown queue does not raise."""
    bus = DashboardEventBus()
    q = asyncio.Queue()
    bus.unsubscribe(q)  # Should not raise
    assert bus.subscriber_count == 0


def test_emit_delivers_to_subscribers():
    """emit() puts events into all subscriber queues."""
    bus = DashboardEventBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()

    bus.emit("messages", {"text": "hello"})

    event1 = q1.get_nowait()
    event2 = q2.get_nowait()

    assert event1 == {"channel": "messages", "data": {"text": "hello"}}
    assert event2 == {"channel": "messages", "data": {"text": "hello"}}


def test_emit_drops_on_full_queue():
    """emit() drops events for subscribers with full queues."""
    bus = DashboardEventBus()
    q = bus.subscribe(maxsize=1)

    # Fill the queue
    bus.emit("ch1", {"n": 1})
    assert not q.empty()

    # This should be dropped (queue full)
    bus.emit("ch2", {"n": 2})

    # Only first event should be in queue
    event = q.get_nowait()
    assert event["data"]["n"] == 1
    assert q.empty()


def test_multiple_channels():
    """emit() works with different channel names."""
    bus = DashboardEventBus()
    q = bus.subscribe()

    bus.emit("messages", {"type": "msg"})
    bus.emit("logs", {"level": "INFO"})
    bus.emit("agents", {"event": "tool_start"})

    events = []
    while not q.empty():
        events.append(q.get_nowait())

    assert len(events) == 3
    assert events[0]["channel"] == "messages"
    assert events[1]["channel"] == "logs"
    assert events[2]["channel"] == "agents"


def test_subscriber_count_property():
    """subscriber_count reflects active subscribers."""
    bus = DashboardEventBus()
    assert bus.subscriber_count == 0

    q1 = bus.subscribe()
    q2 = bus.subscribe()
    assert bus.subscriber_count == 2

    bus.unsubscribe(q1)
    assert bus.subscriber_count == 1

    bus.unsubscribe(q2)
    assert bus.subscriber_count == 0
