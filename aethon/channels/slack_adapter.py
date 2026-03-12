"""Slack Bot adapter using slack-bolt with Socket Mode.

No external server needed — works behind NAT/firewalls.
Listens to message and app_mention events.
"""

import logging

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

logger = logging.getLogger("aethon.slack")


class SlackAdapter(ChannelAdapter):
    """Slack Bot adapter (slack-bolt + Socket Mode)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.bot_token = config.channels.slack.bot_token
        self.app_token = config.channels.slack.app_token
        if not self.bot_token or not self.app_token:
            raise ValueError(
                "Slack bot_token ve app_token gerekli "
                "(config.channels.slack.bot_token, config.channels.slack.app_token)"
            )
        self.app = None
        self.handler = None

    async def start(self) -> None:
        from slack_bolt.async_app import AsyncApp
        from slack_bolt.adapter.socket_mode.async_handler import (
            AsyncSocketModeHandler,
        )

        self.app = AsyncApp(token=self.bot_token)

        @self.app.event("message")
        async def handle_message(event, say):
            if event.get("bot_id"):
                return

            text = event.get("text", "")
            user_id = event.get("user", "unknown")
            thread_ts = event.get("thread_ts")
            channel = event.get("channel", "")
            ts = event.get("ts", "")

            inbound = InboundMessage(
                channel="slack",
                sender_id=user_id,
                sender_name=user_id,
                text=text,
                thread_id=thread_ts,
                raw={"channel": channel, "ts": ts},
            )
            await self.on_message(inbound)

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            await handle_message(event, say)

        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        logger.info("Slack Socket Mode baslatiliyor...")
        await self.handler.start_async()

    async def stop(self) -> None:
        if self.handler:
            await self.handler.close_async()
        logger.info("Slack kapatildi.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.app:
            return

        channel = message.raw.get("channel", message.recipient_id)
        thread_ts = message.thread_id

        await self.app.client.chat_postMessage(
            channel=channel,
            text=message.text,
            thread_ts=thread_ts,
        )
