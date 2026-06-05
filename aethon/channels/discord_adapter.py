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

        channel_id = message.raw.get("channel_id")
        if channel_id:
            channel = self.client.get_channel(channel_id)
        else:
            channel = self.client.get_channel(int(message.recipient_id))

        if channel:
            text = message.text
            if len(text) > 2000:
                chunks = [text[i : i + 2000] for i in range(0, len(text), 2000)]
                for chunk in chunks:
                    await channel.send(chunk)
            else:
                await channel.send(text)
