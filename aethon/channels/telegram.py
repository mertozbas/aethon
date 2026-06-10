"""Telegram Bot adapter using aiogram 3.x.

Supports text messages, photo/document media, and HTML-formatted responses.
Standard Markdown from the model is converted to Telegram-compatible HTML.
"""

import html
import logging
import re

from aethon.channels.base import (
    ChannelAdapter,
    InboundMessage,
    MediaAttachment,
    OutboundMessage,
)

logger = logging.getLogger("aethon.telegram")


def _markdown_to_telegram_html(text: str) -> str:
    """Convert standard Markdown to Telegram-compatible HTML.

    Telegram HTML supports: <b>, <i>, <u>, <s>, <code>, <pre>, <a>.
    Standard Markdown headings (###), bold (**), italic (*), code blocks,
    links, and lists are converted accordingly.
    """
    lines = text.split("\n")
    result = []
    in_code_block = False
    code_block_lines: list[str] = []

    for line in lines:
        # --- code block toggle ---
        if line.strip().startswith("```"):
            if in_code_block:
                # closing code block
                code_content = "\n".join(code_block_lines)
                result.append(f"<pre>{html.escape(code_content)}</pre>")
                code_block_lines = []
                in_code_block = False
            else:
                in_code_block = True
                code_block_lines = []
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        # --- headings: ### Title → <b>Title</b> ---
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            heading_text = _inline_markdown_to_html(heading_match.group(2))
            result.append(f"\n<b>{heading_text}</b>")
            continue

        # --- horizontal rule: --- or *** or ___ ---
        if re.match(r"^[\s]*[-*_]{3,}[\s]*$", line):
            result.append("—" * 20)
            continue

        # apply inline formatting to regular lines
        result.append(_inline_markdown_to_html(line))

    # handle unclosed code block
    if in_code_block and code_block_lines:
        code_content = "\n".join(code_block_lines)
        result.append(f"<pre>{html.escape(code_content)}</pre>")

    return "\n".join(result)


def _inline_markdown_to_html(text: str) -> str:
    """Convert inline Markdown formatting to Telegram HTML.

    Handles: inline code, bold, italic, strikethrough, links.
    """
    # protect inline code first (so inner formatting is not processed)
    code_placeholder = []

    def _save_code(m):
        idx = len(code_placeholder)
        code_placeholder.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00CODE{idx}\x00"

    text = re.sub(r"`([^`]+)`", _save_code, text)

    # escape HTML entities in remaining text (not inside code)
    parts = re.split(r"(\x00CODE\d+\x00)", text)
    escaped_parts = []
    for part in parts:
        if part.startswith("\x00CODE") and part.endswith("\x00"):
            escaped_parts.append(part)
        else:
            escaped_parts.append(html.escape(part))
    text = "".join(escaped_parts)

    # bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # italic: *text* or _text_ (but not inside words like file_name)
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<i>\1</i>", text)

    # strikethrough: ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)

    # links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    # restore inline code
    for idx, code_html in enumerate(code_placeholder):
        text = text.replace(f"\x00CODE{idx}\x00", code_html)

    return text


class TelegramAdapter(ChannelAdapter):
    """Telegram Bot API adapter (aiogram 3.x)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.token = config.channels.telegram.token
        if not self.token:
            raise ValueError(
                "Telegram token required (config.channels.telegram.token or "
                "the TELEGRAM_BOT_TOKEN environment variable)"
            )
        self.bot = None
        self.dp = None

    async def start(self) -> None:
        from aiogram import Bot, Dispatcher, types, F

        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()

        @self.dp.message(F.text)
        async def handle_text(tg_msg: types.Message):
            inbound = InboundMessage(
                channel="telegram",
                sender_id=str(tg_msg.from_user.id),
                sender_name=tg_msg.from_user.full_name or "Unknown",
                text=tg_msg.text,
                reply_to=(
                    str(tg_msg.reply_to_message.message_id)
                    if tg_msg.reply_to_message
                    else None
                ),
                timestamp=tg_msg.date,
                raw={
                    "chat_id": tg_msg.chat.id,
                    "message_id": tg_msg.message_id,
                },
            )
            await self.on_message(inbound)

        @self.dp.message(F.photo)
        async def handle_photo(tg_msg: types.Message):
            photo = tg_msg.photo[-1]
            file_info = await self.bot.get_file(photo.file_id)

            inbound = InboundMessage(
                channel="telegram",
                sender_id=str(tg_msg.from_user.id),
                sender_name=tg_msg.from_user.full_name or "Unknown",
                text=tg_msg.caption or "(image)",
                media=[
                    MediaAttachment(
                        type="image",
                        url=f"https://api.telegram.org/file/bot{self.token}/{file_info.file_path}",
                        filename=f"{photo.file_id}.jpg",
                        mime_type="image/jpeg",
                    )
                ],
                raw={
                    "chat_id": tg_msg.chat.id,
                    "message_id": tg_msg.message_id,
                },
            )
            await self.on_message(inbound)

        @self.dp.message(F.document)
        async def handle_document(tg_msg: types.Message):
            doc = tg_msg.document
            file_info = await self.bot.get_file(doc.file_id)

            inbound = InboundMessage(
                channel="telegram",
                sender_id=str(tg_msg.from_user.id),
                sender_name=tg_msg.from_user.full_name or "Unknown",
                text=tg_msg.caption or f"(file: {doc.file_name})",
                media=[
                    MediaAttachment(
                        type="document",
                        url=f"https://api.telegram.org/file/bot{self.token}/{file_info.file_path}",
                        filename=doc.file_name,
                        mime_type=doc.mime_type,
                    )
                ],
                raw={
                    "chat_id": tg_msg.chat.id,
                    "message_id": tg_msg.message_id,
                },
            )
            await self.on_message(inbound)

        logger.info("Starting Telegram polling...")
        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        if self.dp:
            await self.dp.stop_polling()
        if self.bot:
            await self.bot.session.close()
        logger.info("Telegram shut down.")

    async def send(self, message: OutboundMessage) -> None:
        if not self.bot:
            return
        from aiogram.enums import ParseMode

        chat_id = self._resolve_chat_id(message)
        if chat_id is None:
            logger.warning(
                "Telegram send skipped: no chat_id. Set channels.telegram.chat_id "
                "or security.allowed_senders.telegram, or reply to an inbound message."
            )
            return

        # Convert standard Markdown to Telegram-compatible HTML
        formatted = _markdown_to_telegram_html(message.text)

        if len(formatted) > 4096:
            # For long messages, split on double-newlines to avoid breaking tags
            chunks = self._split_html_message(formatted, 4096)
            for chunk in chunks:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    # Fallback: send raw text chunk without formatting
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message.text[: 4096],
                    )
        else:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=formatted,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.warning("HTML parse failed, sending plain text: %s", e)
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message.text,
                )

    def resolve_recipient(self, message: OutboundMessage):
        return self._resolve_chat_id(message)

    def _resolve_chat_id(self, message: OutboundMessage):
        """Resolve the destination chat id for an outbound message.

        Order: inbound raw (reactive replies) → numeric recipient_id →
        configured ``telegram.chat_id`` → first ``allowed_senders.telegram`` entry.
        Returns a value aiogram accepts (int or str), or ``None`` if nothing resolves
        (proactive send with no configured destination — caller skips instead of crashing).
        """
        raw_id = message.raw.get("chat_id")
        if raw_id is not None:
            return raw_id
        rid = (message.recipient_id or "").strip()
        if rid and rid != "default" and rid.lstrip("-").isdigit():
            return int(rid)
        cfg_id = (self.config.channels.telegram.chat_id or "").strip()
        if cfg_id:
            return cfg_id
        allowed = self.config.security.allowed_senders.get("telegram") or []
        if allowed:
            return allowed[0]
        return None

    @staticmethod
    def _split_html_message(text: str, max_len: int) -> list[str]:
        """Split long HTML message into chunks at paragraph boundaries."""
        chunks = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_len:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks
