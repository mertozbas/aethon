"""Message router.

Routes incoming messages to the agent runtime with sender validation
and session resolution. Emits message events to the dashboard event bus.
"""

import logging
import time

from aethon.channels.base import InboundMessage, OutboundMessage
from aethon.agent.runtime import AethonRuntime
from aethon.config import AethonConfig


logger = logging.getLogger("aethon.router")


class MessageRouter:
    """Route messages between channels and agent runtime."""

    def __init__(self, config: AethonConfig, runtime: AethonRuntime, event_bus=None):
        self.config = config
        self.runtime = runtime
        self.allowed_senders = config.security.allowed_senders
        self._event_bus = event_bus

    async def handle(self, message: InboundMessage) -> OutboundMessage | None:
        """Process an incoming message.

        Args:
            message: Incoming message from any channel.

        Returns:
            Outbound response message, or None if rejected.
        """
        # 1. Sender validation
        if not self._is_allowed(message):
            logger.warning(
                f"REJECTED: {message.sender_id} on {message.channel}"
            )
            return None

        # 2. Resolve session
        session_id = self._resolve_session(message)
        logger.info(f"SESSION: {session_id} | FROM: {message.sender_name}")

        # Emit inbound message event to dashboard
        if self._event_bus:
            self._event_bus.emit("messages", {
                "direction": "inbound",
                "channel_name": message.channel,
                "session_id": session_id,
                "sender": message.sender_name or message.sender_id,
                "content": message.text[:500],  # Truncate for dashboard
                "timestamp": time.time(),
            })

        # 3. Forward to agent runtime
        response_text = await self.runtime.process(message, session_id)

        # Emit outbound response event to dashboard
        if self._event_bus:
            self._event_bus.emit("messages", {
                "direction": "outbound",
                "channel_name": message.channel,
                "session_id": session_id,
                "sender": "AETHON",
                "content": response_text[:500] if response_text else "",
                "timestamp": time.time(),
            })

        # 3b. Ambient mode: record this (real) interaction and surface any pending
        # ambient results. No-op unless an ambient manager is wired.
        ambient = getattr(self.runtime, "_ambient_manager", None)
        if ambient is not None:
            try:
                ambient.record_interaction(message.text, response_text or "")
                pending = ambient.get_and_clear_result()
                extra = "\n\n".join(
                    f"[ambient #{p['iteration']}] {p['result']}"
                    for p in pending
                    if p.get("result")
                )
                if extra:
                    response_text = (response_text or "") + "\n\n---\n" + extra
            except Exception as e:
                logger.warning(f"Ambient integration error: {e}")

        # 4. Build response (raw alanini kopyala — kanal-spesifik veri icin)
        return OutboundMessage(
            channel=message.channel,
            recipient_id=message.sender_id,
            text=response_text,
            raw=message.raw,
        )

    def _is_allowed(self, message: InboundMessage) -> bool:
        """Check if sender is allowed on this channel."""
        channel_allowed = self.allowed_senders.get(message.channel, [])
        if not channel_allowed:
            return True  # Empty allowlist = everyone allowed
        return message.sender_id in channel_allowed

    def _resolve_session(self, message: InboundMessage) -> str:
        """Build session ID from message metadata."""
        if message.thread_id:
            return f"{message.channel}:{message.thread_id}"
        return f"{message.channel}:{message.sender_id}"
