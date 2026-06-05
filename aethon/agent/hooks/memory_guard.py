"""Memory guard hook provider.

Prevents sensitive information (API keys, passwords, tokens, credit cards, SSN)
from being stored in vector memory.
"""

import re
import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent


logger = logging.getLogger("aethon.memory_guard")


class MemoryGuardHookProvider(HookProvider):
    """Block sensitive data from being stored in memory."""

    DEFAULT_PATTERNS = [
        r"(?:api[_-]?key|apikey)\s*[:=]\s*\S+",
        r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
        r"(?:secret|token)\s*[:=]\s*\S+",
        r"(?:ssh-rsa|ssh-ed25519)\s+\S+",
        r"-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
    ]

    def __init__(self, custom_patterns: list[str] | None = None):
        all_patterns = self.DEFAULT_PATTERNS + (custom_patterns or [])
        self._compiled = [re.compile(p, re.IGNORECASE) for p in all_patterns]

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.guard_memory)

    def guard_memory(self, event: BeforeToolCallEvent) -> None:
        """Check memory store calls for sensitive content."""
        if event.tool_use["name"] != "manage_memory":
            return

        tool_input = event.tool_use.get("input", {})
        if tool_input.get("action") != "store":
            return

        content = tool_input.get("content", "")
        if not content:
            return

        for compiled in self._compiled:
            if compiled.search(content):
                event.cancel_tool = (
                    "BLOCKED: An attempt was made to store sensitive information "
                    "(API key, password, token, credit card, SSN) in memory. "
                    "This information is not saved to memory for security reasons."
                )
                logger.warning("MEMORY GUARD: Sensitive information detected")
                return
