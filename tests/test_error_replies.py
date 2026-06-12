"""Tests for user-facing error replies (Phase 9B / H2)."""

import pytest

from aethon.channels.base import (
    ChannelAdapter,
    InboundMessage,
    OutboundMessage,
    build_error_reply,
)


def _msg(text="hello", channel="telegram"):
    return InboundMessage(
        channel=channel, sender_id="u1", sender_name="U", text=text, raw={"chat_id": 9}
    )


def test_build_error_reply_classifies_auth():
    out = build_error_reply(_msg("hi"), RuntimeError("Invalid API key (401)"))
    assert "authentication" in out.text.lower()
    assert "aethon doctor" in out.text


def test_build_error_reply_classifies_quota():
    out = build_error_reply(_msg("hi"), RuntimeError("429 rate limit exceeded"))
    assert "quota" in out.text.lower() or "rate limit" in out.text.lower()


def test_build_error_reply_generic_names_class():
    out = build_error_reply(_msg("hi"), ValueError("weird"))
    assert "ValueError" in out.text


def test_build_error_reply_turkish_for_turkish_message():
    out = build_error_reply(_msg("merhaba günaydın"), RuntimeError("boom"))
    assert "ile kontrol edin" in out.text          # TR hint
    assert "Check with" not in out.text


def test_build_error_reply_english_for_english_message():
    out = build_error_reply(_msg("hello there"), RuntimeError("boom"))
    assert "Check with" in out.text
    assert "kontrol edin" not in out.text


def test_build_error_reply_preserves_routing():
    msg = _msg("hi")
    out = build_error_reply(msg, RuntimeError("x"))
    assert out.channel == "telegram"
    assert out.recipient_id == "u1"
    assert out.raw == {"chat_id": 9}


# --- on_message surfaces the error instead of going silent ------------------


class _RaisingRouter:
    async def handle(self, message):
        raise RuntimeError("model exploded: 401 unauthorized")


class _CaptureAdapter(ChannelAdapter):
    def __init__(self):
        # bypass ChannelAdapter.__init__ wiring; we only need send capture
        self.config = None
        self.router = _RaisingRouter()
        self.sent = []

    async def start(self):  # pragma: no cover - abstract impl
        pass

    async def stop(self):  # pragma: no cover - abstract impl
        pass

    async def send(self, message: OutboundMessage) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_on_message_sends_error_reply_not_silence():
    adapter = _CaptureAdapter()
    await adapter.on_message(_msg("hello"))
    assert len(adapter.sent) == 1                  # not silent
    assert "authentication" in adapter.sent[0].text.lower()
