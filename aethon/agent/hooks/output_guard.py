"""Tool-output guard hook.

Caps how much text a single tool result feeds back to the model. A command that
dumps thousands of lines (ruff, mypy, large greps, verbose builds) would
otherwise overflow the model's context window and abort the turn. The middle of
an oversized result is dropped, keeping the head (and a slice of the tail) plus a
clear truncation marker so the agent still sees the important parts.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent

logger = logging.getLogger("aethon.output_guard")


class ToolOutputGuardHookProvider(HookProvider):
    """Truncate oversized tool-result text before it reaches the model."""

    def __init__(self, max_chars: int = 12000):
        self.max_chars = max_chars

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._cap)

    def _cap(self, event: AfterToolCallEvent) -> None:
        if self.max_chars <= 0:
            return
        try:
            content = event.result.get("content")
        except Exception:
            return
        if not isinstance(content, list):
            return

        # Budget across all text blocks in this result (head-heavy, keep some tail).
        remaining = self.max_chars
        for block in content:
            if not (isinstance(block, dict) and isinstance(block.get("text"), str)):
                continue
            text = block["text"]
            if len(text) <= remaining:
                remaining -= len(text)
                continue
            if remaining <= 0:
                block["text"] = "[... output omitted to fit the model context ...]"
                continue
            head = max(0, remaining * 2 // 3)
            tail = max(0, remaining - head)
            dropped = len(text) - head - tail
            block["text"] = (
                text[:head]
                + f"\n\n[... {dropped} characters truncated to fit the model "
                f"context — re-run on a narrower scope to see the rest ...]\n\n"
                + (text[-tail:] if tail else "")
            )
            logger.info(
                f"Truncated {event.tool_use.get('name', '?')} output "
                f"({len(text)} -> ~{self.max_chars} chars)"
            )
            remaining = 0
