"""Discord Bot adapter using discord.py 2.x.

Responds to DMs and @mentions. Uses channel.id for thread-based sessions.
"""

import logging

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger("aethon.discord")


class DiscordAdapter(ChannelAdapter):
    """Discord Bot adapter (discord.py 2.x)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.token = config.channels.discord.token
        if not self.token:
            raise ValueError(
                "Discord token required (config.channels.discord.token or "
                "the DISCORD_BOT_TOKEN environment variable)"
            )
        self.client = None

    async def start(self) -> None:
        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            logger.info(f"Discord: logged in as {self.client.user}.")

        @self.client.event
        async def on_message(msg: discord.Message):
            if msg.author == self.client.user:
                return

            is_dm = isinstance(msg.channel, discord.DMChannel)
            is_mentioned = (
                self.client.user in msg.mentions if self.client.user else False
            )

            if not (is_dm or is_mentioned):
                return

            text = msg.content
            if self.client.user:
                text = text.replace(f"<@{self.client.user.id}>", "").strip()

            inbound = InboundMessage(
                channel="discord",
                sender_id=str(msg.author.id),
                sender_name=msg.author.display_name,
                text=text,
                thread_id=str(msg.channel.id),
                raw={
                    "channel_id": msg.channel.id,
                    "message_id": msg.id,
                },
            )
            await self.on_message(inbound)

        logger.info("Starting Discord bot...")
        await self.client.start(self.token)

    async def stop(self) -> None:
        if self.client:
            await self.client.close()
        logger.info("Discord shut down.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.client:
            return

        target_id = self._resolve_channel_id(message)
        if target_id is None:
            logger.warning(
                "Discord send skipped: no destination. Set channels.discord.channel_id "
                "or security.allowed_senders.discord, or reply to an inbound message."
            )
            return

        channel = self.client.get_channel(target_id)
        if channel is None:
            channel = await self._fetch_destination(target_id)
        if channel is None:
            logger.warning(f"Discord send skipped: destination {target_id} not reachable.")
            return

        text = message.text
        if len(text) > 2000:
            chunks = [text[i : i + 2000] for i in range(0, len(text), 2000)]
            for chunk in chunks:
                await channel.send(chunk)
        else:
            await channel.send(text)

    def resolve_recipient(self, message: OutboundMessage):
        return self._resolve_channel_id(message)

    def _resolve_channel_id(self, message: OutboundMessage):
        """Resolve the destination channel/user id for an outbound message.

        Order: inbound raw (reactive replies) → numeric recipient_id →
        configured ``discord.channel_id`` → first numeric
        ``allowed_senders.discord`` entry (user id → DM).
        Returns an int id, or ``None`` if nothing resolves (proactive send
        with no configured destination — caller skips instead of crashing).
        """
        raw_id = message.raw.get("channel_id")
        if raw_id is not None:
            return int(raw_id)
        rid = (message.recipient_id or "").strip()
        if rid and rid != "default" and rid.lstrip("-").isdigit():
            return int(rid)
        cfg_id = (self.config.channels.discord.channel_id or "").strip()
        if cfg_id.lstrip("-").isdigit() and cfg_id:
            return int(cfg_id)
        allowed = self.config.security.allowed_senders.get("discord") or []
        for entry in allowed:
            entry = str(entry).strip()
            if entry.lstrip("-").isdigit() and entry:
                return int(entry)
        return None

    async def _fetch_destination(self, target_id: int):
        """Resolve an id missing from the channel cache.

        Tries the id as a channel first, then as a user (opens a DM) — the
        allowed_senders fallback carries user ids, which never appear in the
        channel cache.
        """
        try:
            return await self.client.fetch_channel(target_id)
        except Exception:
            pass
        try:
            user = await self.client.fetch_user(target_id)
            return await user.create_dm()
        except Exception as e:
            logger.warning(f"Discord destination {target_id} not resolvable: {e}")
            return None
