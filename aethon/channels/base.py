"""Base channel adapter and message models."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger("aethon.channels")


@dataclass
class MediaAttachment:
    """Media attachment for messages."""

    type: str  # "image", "audio", "video", "document"
    url: Optional[str] = None
    data: Optional[bytes] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class InboundMessage:
    """Incoming message from any channel."""

    channel: str  # "cli", "webchat", "telegram", ...
    sender_id: str
    sender_name: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)


@dataclass
class OutboundMessage:
    """Outgoing message to any channel."""

    channel: str
    recipient_id: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ApprovalRequest:
    """A pending tool-approval question routed back to a channel (Phase 9A / S6).

    Built from a strands interrupt's ``reason`` (the approval hook sets
    ``{tool, parameters, message}``) plus the originating sender. Channels turn
    it into a yes/no prompt; the answer resumes the paused agent turn.
    """

    interrupt_id: str
    tool: str
    parameters: dict
    message: str
    session_id: str
    recipient_id: str


class ChannelAdapter(ABC):
    """Base class for all channel adapters."""

    def __init__(self, config, router):
        self.config = config
        self.router = router

    @abstractmethod
    async def start(self) -> None:
        """Start listening on this channel."""

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the channel."""

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None:
        """Send a message through this channel."""

    def resolve_recipient(self, message: OutboundMessage):
        """Resolve the delivery destination for an outbound message.

        Returns a channel-specific destination, or ``None`` when the message
        has no deliverable recipient (so callers can report a real error
        instead of claiming success). Channels without an addressing concept
        (CLI, WebChat) keep this default and accept everything.
        """
        return message.recipient_id or "default"

    async def on_message(self, message: InboundMessage) -> None:
        """Forward incoming message to router."""
        response = await self.router.handle(message)
        if response:
            try:
                await self.send(response)
            except Exception as e:
                # The reactive path owns delivery failures: adapters' send()
                # may raise (deliberately — the send_message tool reports the
                # real outcome), but a lost reply must still be logged here
                # rather than vanish into the channel framework.
                logger.error(
                    f"Reply delivery failed ({message.channel}): {e}"
                )

    async def ask_approval(self, request: "ApprovalRequest") -> Optional[bool]:
        """Ask the user to approve a tool call mid-turn (Phase 9A / S6).

        Returns ``True`` (approved) / ``False`` (denied), or ``None`` when this
        channel cannot answer — the runtime then fails closed (denies) with a
        clear message rather than wedging the session. Channels that can answer
        override this; the base default advertises "cannot answer".
        """
        return None
