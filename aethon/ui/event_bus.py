"""Dashboard event bus.

In-process asyncio event bus for broadcasting real-time events to dashboard
WebSocket clients. Supports multiple subscribers with bounded queues — slow
consumers drop events.

``emit()`` is safe to call from any thread: the agent runs in a thread-pool
executor, so telemetry hooks, the log handler, and the router emit from a worker
thread while the subscriber queues are bound to the gateway's main event loop.
Puts are therefore scheduled onto the loop with ``call_soon_threadsafe`` rather
than touched directly (``asyncio.Queue`` is not thread-safe).
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger("aethon.event_bus")


class DashboardEventBus:
    """Broadcast events to multiple async subscribers (thread-safe emit)."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe(self, maxsize: int = 1000) -> asyncio.Queue:
        """Create a new subscriber queue (call from within the event loop)."""
        # Capture the running loop so emit() from worker threads can schedule puts.
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    @staticmethod
    def _safe_put(q: asyncio.Queue, event: dict) -> None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Drop events for slow consumers.

    def emit(self, channel: str, data: dict[str, Any]) -> None:
        """Emit an event to all subscribers. Safe to call from any thread.

        Args:
            channel: Event channel name (e.g. "messages", "telemetry", "agents", "logs").
            data: Event payload dict.
        """
        if not self._subscribers:
            return
        event = {"channel": channel, "data": data}
        loop = self._loop
        if loop is None or not loop.is_running():
            # No loop captured yet (or it has stopped) — best-effort same-thread put.
            for q in list(self._subscribers):
                self._safe_put(q, event)
            return
        # Schedule the put on the loop's thread (thread-safe).
        for q in list(self._subscribers):
            try:
                loop.call_soon_threadsafe(self._safe_put, q, event)
            except RuntimeError:
                pass  # Loop closed between the check and the call.

    @property
    def subscriber_count(self) -> int:
        """Number of active subscribers."""
        return len(self._subscribers)
