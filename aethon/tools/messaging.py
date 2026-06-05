"""Cross-channel messaging tool.

Allows agents to send messages to other channels (Telegram, Discord, Slack, etc).
Uses global state pattern (same as delegate.py).
"""

import asyncio
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

    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is not None:
            # Already inside an event loop (e.g. async caller) — schedule it.
            asyncio.ensure_future(adapter.send(outbound))
        else:
            # No running loop (sync caller / worker thread) — run to completion.
            asyncio.run(adapter.send(outbound))
        return f"Message sent via {channel}."
    except Exception as e:
        logger.error(f"Message send error: {e}")
        return f"Error: Could not send message ({e})"
