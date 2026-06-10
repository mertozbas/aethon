"""Anglicization guard hook (Phase 8 / R14).

Enforces a documented user preference as code: existing non-English
(Turkish) text must not be silently rewritten into English during edits.
Watches replace-style edits (editor str_replace, edit tools): when the text
being REPLACED contains Turkish-specific characters and the replacement
contains none, the call is cancelled once with a reminder. Re-issuing the
identical edit goes through (an explicit, post-reminder decision) — unless
``reliability.strict`` is set, which always blocks.

Heuristic by design: it will miss ASCII-only Turkish and that is fine —
advisory, tuned against false positives.
"""

import hashlib
import logging
import re
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent

logger = logging.getLogger("aethon.anglicization_guard")

GUARDED_TOOLS = {"editor", "edit", "file_write"}

# Characters that exist in Turkish but not in English text.
_TR_CHARS = re.compile(r"[çğışüöÇĞİŞÜÖ]")

# (old, new) key pairs used by the replace-style tools.
_REPLACE_KEY_PAIRS = [
    ("old_str", "new_str"),
    ("old_string", "new_string"),
    ("old_text", "new_text"),
]

REMINDER = (
    "PAUSED: this edit replaces existing Turkish text with English-only "
    "text. Rule: never anglicize existing non-English content unless the "
    "user explicitly asked for a translation. If the user did ask, re-issue "
    "the same edit and it will go through; otherwise keep the original "
    "language."
)


class AnglicizationGuardHookProvider(HookProvider):
    """Stop silent TR→EN rewrites of existing text."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self._reminded: set[str] = set()

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check_edit)

    def check_edit(self, event: BeforeToolCallEvent) -> None:
        tool_name = str(event.tool_use.get("name", "")).lower()
        if tool_name not in GUARDED_TOOLS:
            return
        tool_input = event.tool_use.get("input", {}) or {}

        for old_key, new_key in _REPLACE_KEY_PAIRS:
            old = tool_input.get(old_key)
            new = tool_input.get(new_key)
            if not isinstance(old, str) or not isinstance(new, str) or not new.strip():
                continue
            if not self._anglicizes(old, new):
                continue

            fingerprint = hashlib.sha256(
                f"{old}\x00{new}".encode("utf-8")
            ).hexdigest()
            if not self.strict and fingerprint in self._reminded:
                # Identical edit re-issued after the reminder — an explicit
                # decision; let it through (advisory mode).
                return
            self._reminded.add(fingerprint)
            event.cancel_tool = REMINDER
            logger.warning(
                f"Anglicization guard: TR→EN replacement paused ({tool_name})"
            )
            return

    @staticmethod
    def _anglicizes(old: str, new: str) -> bool:
        """True when Turkish-specific characters disappear in the replacement."""
        return bool(_TR_CHARS.search(old)) and not _TR_CHARS.search(new)
