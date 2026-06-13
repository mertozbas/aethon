"""Cross-channel messaging tool.

Allows agents to send messages to other channels (Telegram, Discord, Slack, etc).
Uses global state pattern (same as delegate.py).
"""

import asyncio
import concurrent.futures
import logging

from strands import tool

from aethon.channels.base import OutboundMessage


logger = logging.getLogger("aethon.messaging")

_gateway = None


def set_gateway(gateway):
    """Set the global gateway reference (called from AethonGateway)."""
    global _gateway
    _gateway = gateway


def get_gateway():
    """Get the global gateway reference."""
    return _gateway


_SEND_TIMEOUT_SECONDS = 30

# Strong references to in-flight fire-and-forget sends: the event loop keeps
# only weak references to tasks, so an unreferenced send could be garbage
# collected mid-flight.
_pending_sends: set = set()


def _log_send_failure(task: "asyncio.Task") -> None:
    """Surface a failed fire-and-forget send in the log (in-loop path)."""
    _pending_sends.discard(task)
    if task.cancelled():
        logger.error("Async message send was cancelled before completing.")
        return
    exc = task.exception()
    if exc:
        logger.error(f"Async message send failed: {exc}")


@tool
def send_message(channel: str, text: str, recipient: str = "") -> str:
    """Send a message to the specified channel.
    Use this, for example, to send a notification to Telegram or deliver a report to a Slack channel.

    Args:
        channel: Target channel ("telegram", "discord", "slack", "webchat")
        text: Message text to send
        recipient: Recipient ID (default user if empty)
    """
    if not _gateway:
        return "Error: Gateway not started."

    adapter = _gateway.adapters.get(channel)
    if not adapter:
        available = list(_gateway.adapters.keys())
        return f"Channel not found or not enabled: {channel}. Available: {available}"

    outbound = OutboundMessage(
        channel=channel,
        recipient_id=recipient or "default",
        text=text,
    )

    # Validate the destination BEFORE dispatch so the tool never reports
    # success for a message that cannot be delivered (proactive send with no
    # configured recipient used to be silently dropped by the adapter).
    resolve = getattr(adapter, "resolve_recipient", None)
    if callable(resolve):
        try:
            resolved = resolve(outbound)
        except Exception as e:
            logger.error(f"Recipient resolution error ({channel}): {e}")
            return f"Error: Could not resolve recipient ({e})"
        if resolved is None:
            return (
                f"Error: {channel} has no deliverable recipient. Pass "
                f"`recipient` explicitly or configure a default destination "
                f"for the channel (e.g. channels.{channel} default recipient "
                f"or security.allowed_senders.{channel})."
            )

    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is not None:
            # On the event loop thread itself — blocking here would deadlock
            # the loop. The recipient is already validated; schedule the send
            # and surface any late failure in the log. Phrase the result
            # honestly: the send has not completed yet.
            task = asyncio.ensure_future(adapter.send(outbound))
            _pending_sends.add(task)
            task.add_done_callback(_log_send_failure)
            return f"Message queued for delivery via {channel}."

        gateway_loop = getattr(_gateway, "loop", None)
        if gateway_loop is not None and gateway_loop.is_running():
            # Worker thread (the normal tool-executor path): run the send on
            # the loop the adapter clients live on and wait for the real
            # outcome — a crashed send must not report success.
            future = asyncio.run_coroutine_threadsafe(
                adapter.send(outbound), gateway_loop
            )
            try:
                future.result(timeout=_SEND_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                # `Future.result(timeout=...)` raises concurrent.futures.TimeoutError.
                # On Python 3.10 that is a DISTINCT class from builtins.TimeoutError,
                # so `except TimeoutError` silently missed it there — the send fell
                # through to the generic handler and was never cancelled (the exact
                # late-delivery bug this guards against). 3.11+ merged the two; catch
                # the concurrent.futures one so cancellation fires on all versions.
                # A timed-out send must not deliver later — the agent was told it
                # failed and may retry (duplicate deliveries).
                future.cancel()
                return (
                    f"Error: send via {channel} timed out after "
                    f"{_SEND_TIMEOUT_SECONDS}s and was cancelled."
                )
        else:
            # No gateway loop (tests / standalone use) — run to completion.
            asyncio.run(adapter.send(outbound))
        return f"Message sent via {channel}."
    except Exception as e:
        logger.error(f"Message send error: {e}")
        return f"Error: Could not send message ({e})"
