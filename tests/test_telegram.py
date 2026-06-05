"""Tests for TelegramAdapter."""

import pytest

from aethon.config import AethonConfig, TelegramChannelConfig, ChannelsConfig
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
