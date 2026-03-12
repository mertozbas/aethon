"""Base channel adapter and message models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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

    async def on_message(self, message: InboundMessage) -> None:
        """Forward incoming message to router."""
        response = await self.router.handle(message)
        if response:
            await self.send(response)
