"""Base channel adapter and message models."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger("aethon.channels")

# Turkish-specific characters — pick the reply language from the user's message.
_TR_CHARS = re.compile(r"[çğışüöÇĞİŞÜÖ]")

# Map a substring found in the error text to a (TR, EN) user-facing explanation.
# Order matters — first match wins.
_ERROR_CLASSES = [
    (("api key", "api_key", "unauthorized", "authentication", "401", "invalid_api_key", "no api key"),
     ("Sağlayıcı kimlik doğrulaması başarısız (API anahtarı?).",
      "Provider authentication failed (API key?).")),
    (("rate limit", "ratelimit", "quota", "429", "insufficient_quota", "too many requests"),
     ("Sağlayıcı kota/oran sınırı aşıldı, biraz sonra tekrar deneyin.",
      "Provider quota/rate limit hit — try again shortly.")),
    (("timed out", "timeout"),
     ("İşlem zaman aşımına uğradı, tekrar deneyin.",
      "The request timed out — please try again.")),
    (("model", "not found", "404", "does not exist", "no such model"),
     ("Model bulunamadı veya yanlış yapılandırılmış.",
      "Model not found or misconfigured.")),
]


def build_error_reply(message: "InboundMessage", exc: Exception) -> "OutboundMessage":
    """A short, localized last-resort reply so a failed turn is never silent (H2).

    Classifies common provider failures (auth/quota/timeout/model) and falls
    back to a generic message naming the exception class. Language follows the
    user's message (Turkish if it contains Turkish characters).
    """
    tr = bool(_TR_CHARS.search(message.text or ""))
    blob = f"{type(exc).__name__}: {exc}".lower()
    detail = None
    for needles, (tr_msg, en_msg) in _ERROR_CLASSES:
        if any(n in blob for n in needles):
            detail = tr_msg if tr else en_msg
            break
    if detail is None:
        detail = (
            f"Bir hata oluştu ({type(exc).__name__})."
            if tr
            else f"Something went wrong ({type(exc).__name__})."
        )
    hint = " `aethon doctor` ile kontrol edin." if tr else " Check with `aethon doctor`."
    return OutboundMessage(
        channel=message.channel,
        recipient_id=message.sender_id,
        text=detail + hint,
        raw=message.raw,
    )


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

    #: Whether ``start()`` blocks for the channel's lifetime (a polling loop or
    #: server). The supervisor treats a clean return from a blocking channel as
    #: an unexpected stop and restarts it; a non-blocking channel (one that hands
    #: off to a background client and returns) is done when ``start()`` returns.
    blocking: bool = True

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
        """Forward incoming message to router, with progress + error handling."""
        try:
            async with self.typing_context(message):
                response = await self.router.handle(message)
        except Exception as e:
            # H2: a model/runtime failure must never leave the bot silent —
            # surface a short, localized error reply instead.
            logger.error(
                f"Turn failed ({message.channel}): {type(e).__name__}: {e}",
                exc_info=True,
            )
            response = build_error_reply(message, e)
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

    def typing_context(self, message: "InboundMessage"):
        """Per-channel "working…" progress signal for the duration of a turn (H5).

        The base is a no-op; channels that support a typing indicator override
        this to return an async context manager.
        """
        import contextlib

        return contextlib.nullcontext()

    async def ask_approval(self, request: "ApprovalRequest") -> Optional[bool]:
        """Ask the user to approve a tool call mid-turn (Phase 9A / S6).

        Returns ``True`` (approved) / ``False`` (denied), or ``None`` when this
        channel cannot answer — the runtime then fails closed (denies) with a
        clear message rather than wedging the session. Channels that can answer
        override this; the base default advertises "cannot answer".
        """
        return None
