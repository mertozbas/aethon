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
    """Belirtilen kanala mesaj gonder.
    Ornegin Telegram'a bildirim gondermek veya Slack kanalina rapor iletmek icin kullan.

    Args:
        channel: Hedef kanal ("telegram", "discord", "slack", "webchat")
        text: Gonderilecek mesaj metni
        recipient: Alici ID (bos ise varsayilan kullanici)
    """
    if not _gateway:
        return "Hata: Gateway baslatilmamis."

    adapter = _gateway.adapters.get(channel)
    if not adapter:
        available = list(_gateway.adapters.keys())
        return f"Kanal bulunamadi veya etkin degil: {channel}. Mevcut: {available}"

    outbound = OutboundMessage(
        channel=channel,
        recipient_id=recipient or "default",
        text=text,
    )

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(adapter.send(outbound))
        else:
            loop.run_until_complete(adapter.send(outbound))
        return f"Mesaj {channel} uzerinden gonderildi."
    except Exception as e:
        logger.error(f"Mesaj gonderme hatasi: {e}")
        return f"Hata: Mesaj gonderilemedi ({e})"
