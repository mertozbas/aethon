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
                "Slack bot_token and app_token required "
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
        logger.info("Starting Slack Socket Mode...")
        await self.handler.start_async()

    async def stop(self) -> None:
        if self.handler:
            await self.handler.close_async()
        logger.info("Slack shut down.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.app:
            return

        channel = self._resolve_channel(message)
        if channel is None:
            logger.warning(
                "Slack send skipped: no channel. Set channels.slack.channel "
                "or security.allowed_senders.slack, or reply to an inbound message."
            )
            return

        await self.app.client.chat_postMessage(
            channel=channel,
            text=message.text,
            thread_ts=message.thread_id,
        )

    def _resolve_channel(self, message: OutboundMessage):
        """Resolve the destination channel for an outbound message.

        Order: inbound raw (reactive replies) → explicit recipient_id →
        configured ``slack.channel`` → first ``allowed_senders.slack`` entry
        (a user id opens the app's DM with that user).
        Returns a Slack channel/user id, or ``None`` if nothing resolves
        (proactive send with no configured destination — caller skips
        instead of passing 'default' to the API).
        """
        raw_channel = message.raw.get("channel")
        if raw_channel:
            return raw_channel
        rid = (message.recipient_id or "").strip()
        if rid and rid != "default":
            return rid
        cfg = (self.config.channels.slack.channel or "").strip()
        if cfg:
            return cfg
        allowed = self.config.security.allowed_senders.get("slack") or []
        if allowed:
            return allowed[0]
        return None
