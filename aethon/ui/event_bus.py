"""Dashboard event bus.

In-process asyncio event bus for broadcasting real-time events
to dashboard WebSocket clients. Supports multiple subscribers
with bounded queues — slow consumers drop events.
"""

import asyncio
import logging
from typing import Any


logger = logging.getLogger("aethon.event_bus")


class DashboardEventBus:
    """Broadcast events to multiple async subscribers."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        """Create a new subscriber queue.

        Args:
            maxsize: Maximum queue size before events are dropped.

        Returns:
            An asyncio.Queue that receives all emitted events.
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def emit(self, channel: str, data: dict[str, Any]) -> None:
        """Emit an event to all subscribers.

        Events are dropped for subscribers whose queues are full.

        Args:
            channel: Event channel name (e.g. "messages", "telemetry", "agents", "logs").
            data: Event payload dict.
        """
        event = {"channel": channel, "data": data}
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events for slow consumers

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscribers)
