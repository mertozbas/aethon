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
            from neonize.utils import log as neonize_log
        except ImportError:
            raise ImportError(
                "WhatsApp icin neonize gerekli: pip install neonize"
            )

        self.client = NewClient("aethon_session")

        @self.client.event(ConnectedEv)
        def on_connected(_client, _event):
            logger.info("WhatsApp: baglandi.")

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

        logger.info("WhatsApp: QR kod eslestirmesi bekleniyor...")
        self.client.connect()

    async def stop(self) -> None:
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        logger.info("WhatsApp kapatildi.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.client:
            return

        try:
            from neonize.utils.jid import build_jid

            chat = message.raw.get("chat", message.recipient_id)
            jid = build_jid(chat)
            self.client.send_message(jid, message.text)
        except Exception as e:
            logger.error(f"WhatsApp mesaj gonderme hatasi: {e}")
