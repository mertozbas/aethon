"""WhatsApp adapter using neonize (experimental).

This adapter is experimental — neonize library is relatively new and may be unstable.
Requires QR code pairing on first run.
"""

import logging

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger("aethon.whatsapp")


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp adapter (neonize — experimental)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.client = None

    async def start(self) -> None:
        try:
            from neonize.client import NewClient
            from neonize.events import MessageEv, ConnectedEv
        except ImportError:
            raise ImportError(
                "WhatsApp requires neonize: pip install neonize"
            )

        self.client = NewClient("aethon_session")

        @self.client.event(ConnectedEv)
        def on_connected(_client, _event):
            logger.info("WhatsApp: connected.")

        @self.client.event(MessageEv)
        def on_message(_client, event):
            import asyncio

            msg = event.Message
            if not msg.conversation and not msg.extendedTextMessage:
                return

            text = msg.conversation or (
                msg.extendedTextMessage.text
                if msg.extendedTextMessage
                else ""
            )
            sender = event.Info.MessageSource.Sender.User
            chat = event.Info.MessageSource.Chat.User

            inbound = InboundMessage(
                channel="whatsapp",
                sender_id=sender,
                sender_name=sender,
                text=text,
                raw={"chat": chat, "sender": sender},
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.on_message(inbound))
            else:
                loop.run_until_complete(self.on_message(inbound))

        logger.info("WhatsApp: waiting for QR code pairing...")
        self.client.connect()

    async def stop(self) -> None:
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        logger.info("WhatsApp shut down.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.client:
            return

        chat = self._resolve_chat(message)
        if chat is None:
            logger.warning(
                "WhatsApp send skipped: no chat. Set channels.whatsapp.chat "
                "or security.allowed_senders.whatsapp, or reply to an inbound message."
            )
            return

        from neonize.utils.jid import build_jid

        # No blanket except here: a failed send must propagate so callers
        # (send_message tool, router) report the real outcome instead of "sent".
        jid = build_jid(chat)
        self.client.send_message(jid, message.text)

    def resolve_recipient(self, message: OutboundMessage):
        return self._resolve_chat(message)

    def _resolve_chat(self, message: OutboundMessage):
        """Resolve the destination chat for an outbound message.

        Order: inbound raw (reactive replies) → explicit recipient_id →
        configured ``whatsapp.chat`` → first ``allowed_senders.whatsapp``
        entry. Returns a chat user id, or ``None`` if nothing resolves
        (proactive send with no configured destination — caller skips
        instead of building a 'default' JID).
        """
        raw_chat = message.raw.get("chat")
        if raw_chat:
            return raw_chat
        rid = (message.recipient_id or "").strip()
        if rid and rid != "default":
            return rid
        cfg = (self.config.channels.whatsapp.chat or "").strip()
        if cfg:
            return cfg
        allowed = self.config.security.allowed_senders.get("whatsapp") or []
        if allowed:
            return allowed[0]
        return None
