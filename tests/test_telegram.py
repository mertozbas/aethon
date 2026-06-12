"""Tests for TelegramAdapter."""

import asyncio

import pytest
from unittest.mock import AsyncMock

from aethon.config import AethonConfig, TelegramChannelConfig, ChannelsConfig
from aethon.channels.base import ApprovalRequest
from aethon.channels.telegram import (
    _markdown_to_telegram_html,
    _inline_markdown_to_html,
)


def test_telegram_adapter_requires_token():
    """TelegramAdapter raises ValueError without token."""
    config = AethonConfig(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=True, token=""),
        )
    )
    from aethon.channels.telegram import TelegramAdapter

    with pytest.raises(ValueError, match="Telegram token required"):
        TelegramAdapter(config, router=None)


def test_telegram_adapter_creates_with_token():
    """TelegramAdapter creates successfully with token."""
    config = AethonConfig(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=True, token="123456:ABC-DEF"),
        )
    )
    from aethon.channels.telegram import TelegramAdapter

    adapter = TelegramAdapter(config, router=None)
    assert adapter.token == "123456:ABC-DEF"
    assert adapter.bot is None
    assert adapter.dp is None


def test_telegram_adapter_is_channel_adapter():
    """TelegramAdapter inherits from ChannelAdapter."""
    from aethon.channels.telegram import TelegramAdapter
    from aethon.channels.base import ChannelAdapter

    assert issubclass(TelegramAdapter, ChannelAdapter)


# --- _resolve_chat_id (proactive/outbound destination) tests ---


def _adapter(*, chat_id="", allowed=None):
    from aethon.config import AethonConfig, SecurityConfig
    from aethon.channels.telegram import TelegramAdapter

    config = AethonConfig(
        channels=ChannelsConfig(
            telegram=TelegramChannelConfig(enabled=True, token="123:ABC", chat_id=chat_id),
        ),
        security=SecurityConfig(allowed_senders={"telegram": allowed} if allowed else {}),
    )
    return TelegramAdapter(config, router=None)


def _out(recipient_id="default", raw=None):
    from aethon.channels.base import OutboundMessage

    return OutboundMessage(channel="telegram", recipient_id=recipient_id, text="hi", raw=raw or {})


def test_resolve_chat_id_prefers_inbound_raw():
    """Reactive replies use the inbound chat id regardless of config."""
    adapter = _adapter(chat_id="999")
    assert adapter._resolve_chat_id(_out(recipient_id="42", raw={"chat_id": 7})) == 7


def test_resolve_chat_id_numeric_recipient():
    adapter = _adapter()
    assert adapter._resolve_chat_id(_out(recipient_id="-100123")) == -100123


def test_resolve_chat_id_default_falls_back_to_config():
    """Proactive send with recipient 'default' must NOT crash (old int('default')) — it
    resolves to the configured chat_id."""
    adapter = _adapter(chat_id="555")
    assert adapter._resolve_chat_id(_out(recipient_id="default")) == "555"


def test_resolve_chat_id_falls_back_to_allowed_senders():
    adapter = _adapter(allowed=["6875048694"])
    assert adapter._resolve_chat_id(_out(recipient_id="default")) == "6875048694"


def test_resolve_chat_id_none_when_nothing_configured():
    adapter = _adapter()
    assert adapter._resolve_chat_id(_out(recipient_id="default")) is None


# --- Markdown to Telegram HTML converter tests ---


def test_heading_conversion():
    """### Heading becomes <b>Heading</b>."""
    result = _markdown_to_telegram_html("### Merhaba Dunya")
    assert "<b>Merhaba Dunya</b>" in result
    assert "###" not in result


def test_multiple_heading_levels():
    """All heading levels (h1-h6) become bold."""
    text = "# H1\n## H2\n### H3\n#### H4"
    result = _markdown_to_telegram_html(text)
    assert "<b>H1</b>" in result
    assert "<b>H2</b>" in result
    assert "<b>H3</b>" in result
    assert "<b>H4</b>" in result
    assert "#" not in result


def test_bold_conversion():
    """**bold** becomes <b>bold</b>."""
    result = _inline_markdown_to_html("Bu **onemli** bir kelime")
    assert "<b>onemli</b>" in result
    assert "**" not in result


def test_italic_conversion():
    """*italic* becomes <i>italic</i>."""
    result = _inline_markdown_to_html("Bu *vurgulu* bir kelime")
    assert "<i>vurgulu</i>" in result


def test_inline_code_conversion():
    """`code` becomes <code>code</code>."""
    result = _inline_markdown_to_html("Kullan: `pip install aethon`")
    assert "<code>pip install aethon</code>" in result
    assert "`" not in result.replace("<code>", "").replace("</code>", "")


def test_code_block_conversion():
    """```code block``` becomes <pre>code block</pre>."""
    text = "Ornek:\n```\nprint('hello')\nx = 42\n```\nBitti."
    result = _markdown_to_telegram_html(text)
    assert "<pre>" in result
    assert "print(&#x27;hello&#x27;)" in result  # html-escaped
    assert "```" not in result


def test_link_conversion():
    """[text](url) becomes <a href="url">text</a>."""
    result = _inline_markdown_to_html("Bak: [Google](https://google.com)")
    assert '<a href="https://google.com">Google</a>' in result


def test_strikethrough_conversion():
    """~~text~~ becomes <s>text</s>."""
    result = _inline_markdown_to_html("Bu ~~yanlis~~ dogru")
    assert "<s>yanlis</s>" in result


def test_html_entities_escaped():
    """< and > in text are escaped to prevent injection."""
    result = _inline_markdown_to_html("a < b > c & d")
    assert "&lt;" in result
    assert "&gt;" in result
    assert "&amp;" in result


# --- S6: answerable approval (inline keyboard + callback) -------------------


def _approval_request(recipient_id="42", iid="i1"):
    return ApprovalRequest(
        interrupt_id=iid,
        tool="shell",
        parameters={"command": "ls"},
        message="'shell' calistirilmak isteniyor. Onayla?",
        session_id="telegram:42",
        recipient_id=recipient_id,
    )


def test_callback_resolves_pending_future():
    """A matching callback resolves the parked approval future to its decision."""
    adapter = _adapter(allowed=["42"])
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    adapter._pending["tok1"] = fut
    authorized, decision = adapter._approval_decision_from_callback("apr:tok1:1", 42)
    assert authorized is True and decision is True
    assert fut.result() is True
    loop.close()


def test_callback_denies():
    adapter = _adapter(allowed=["42"])
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    adapter._pending["tok2"] = fut
    authorized, decision = adapter._approval_decision_from_callback("apr:tok2:0", 42)
    assert authorized is True and decision is False
    assert fut.result() is False
    loop.close()


def test_callback_rejects_unauthorized_presser():
    """A user not on the allowlist can't answer someone else's approval."""
    adapter = _adapter(allowed=["42"])
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    adapter._pending["tok3"] = fut
    authorized, decision = adapter._approval_decision_from_callback("apr:tok3:1", 999)
    assert authorized is False
    assert not fut.done()  # future untouched — stranger can't approve
    loop.close()


def test_callback_rejects_different_allowlisted_user():
    """Even an allowlisted bystander can't answer another user's pending approval."""
    adapter = _adapter(allowed=["42", "43"])
    loop = asyncio.new_event_loop()
    fut = loop.create_future()
    adapter._pending["tok4"] = fut
    adapter._pending_owner["tok4"] = "42"  # owned by user 42
    authorized, decision = adapter._approval_decision_from_callback("apr:tok4:1", 43)
    assert authorized is False           # user 43 is allowlisted but not the owner
    assert not fut.done()
    # The owner themselves can answer.
    authorized2, decision2 = adapter._approval_decision_from_callback("apr:tok4:1", 42)
    assert authorized2 is True and decision2 is True
    loop.close()


@pytest.mark.asyncio
async def test_ask_approval_sends_keyboard_and_awaits():
    """ask_approval sends an inline keyboard and resolves on the callback."""
    adapter = _adapter(allowed=["42"])
    adapter.bot = AsyncMock()
    task = asyncio.ensure_future(adapter.ask_approval(_approval_request("42")))
    await asyncio.sleep(0)  # let the message send + the future register
    adapter.bot.send_message.assert_awaited_once()
    kwargs = adapter.bot.send_message.await_args.kwargs
    assert kwargs["chat_id"] == 42
    # Extract the callback token from the keyboard and resolve it.
    kb = kwargs["reply_markup"]
    token = kb.inline_keyboard[0][0].callback_data.split(":")[1]
    adapter._approval_decision_from_callback(f"apr:{token}:1", 42)
    assert await task is True


@pytest.mark.asyncio
async def test_ask_approval_no_destination_fails_closed():
    adapter = _adapter()  # no chat_id, no allowlist → no destination
    adapter.bot = AsyncMock()
    assert await adapter.ask_approval(_approval_request("default")) is None


def test_code_block_content_escaped():
    """HTML inside code blocks is escaped."""
    text = "```\n<script>alert('xss')</script>\n```"
    result = _markdown_to_telegram_html(text)
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_plain_text_unchanged():
    """Plain text without Markdown passes through (with HTML escaping)."""
    result = _markdown_to_telegram_html("Merhaba, nasilsin?")
    assert "Merhaba, nasilsin?" in result


def test_mixed_formatting():
    """Mixed Markdown converts correctly."""
    text = "### Baslik\n\nBu **kalin** ve *italik* bir `kod` ornegi."
    result = _markdown_to_telegram_html(text)
    assert "<b>Baslik</b>" in result
    assert "<b>kalin</b>" in result
    assert "<i>italik</i>" in result
    assert "<code>kod</code>" in result


def test_horizontal_rule():
    """--- becomes em-dash line."""
    result = _markdown_to_telegram_html("Paragraf 1\n---\nParagraf 2")
    assert "—" in result
    assert "---" not in result


def test_split_html_message():
    """Long messages are split at paragraph boundaries."""
    from aethon.channels.telegram import TelegramAdapter

    long_text = "\n".join([f"Satir {i}" for i in range(100)])
    chunks = TelegramAdapter._split_html_message(long_text, 200)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 200


def test_resolve_chat_id_malformed_numeric_falls_through():
    """Review fix: '--123' passed isdigit-after-lstrip but crashed int();
    it now falls through to the configured default instead."""
    adapter = _adapter(chat_id="555")
    assert adapter._resolve_chat_id(_out(recipient_id="--123")) == "555"
