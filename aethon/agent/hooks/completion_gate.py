"""Definition-of-Done completion gate (Phase 8 / R6).

Watches the final assistant message of each invocation: when it asserts
success (tests pass / done / tamamlandı / geçti ...) while file edits
happened with no PASS verification evidence (PostEditVerify, R7), it records
a reminder that the runtime appends to the reply — the agent's word alone no
longer returns as ground truth. Advisory by default; with
``reliability.strict`` the runtime re-prompts the agent once to verify or
retract before answering.
"""

import logging
import re
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterInvocationEvent

logger = logging.getLogger("aethon.completion_gate")

# TR + EN success assertions. Deliberately word-bounded and conservative —
# false positives nag, so tune here before ever considering strict mode.
_SUCCESS_RE = re.compile(
    r"\b("
    r"passed|tests? pass|done|completed|ready|fixed|works now|all green"
    r"|tamamland[ıi]|bitti|ge[çc]ti|d[üu]zeltildi|haz[ıi]r|[çc]al[ıi][şs][ıi]yor"
    r")\b",
    re.IGNORECASE,
)

DOD_REMINDER = (
    "[Completion Gate] This reply asserts success, but no PASS verification "
    "evidence was recorded for the files edited in this session. Run the "
    "relevant checks (lint/type/tests) and report the result, or explicitly "
    "retract the claim."
)


class CompletionGateHookProvider(HookProvider):
    """Flag success claims that carry no verification evidence."""

    def __init__(self, config, verify_hook=None):
        self.config = config  # ReliabilityConfig
        self.verify_hook = verify_hook  # PostEditVerifyHookProvider | None
        self._pending_note: str | None = None

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterInvocationEvent, self._on_after_invocation)

    def _on_after_invocation(self, event: AfterInvocationEvent) -> None:
        try:
            text = self._final_assistant_text(event.agent)
            if not text or not _SUCCESS_RE.search(text):
                return
            vh = self.verify_hook
            if vh is None or vh.edits_seen == 0:
                # Conversational "done" with no edits in the window — fine.
                return
            if vh.last_outcome == "pass":
                # Claim is backed by evidence; start a fresh edit window.
                vh.edits_seen = 0
                return
            self._pending_note = DOD_REMINDER
            # Flag once per edit window — repeating the same nag every turn
            # without new edits would only train the agent to ignore it.
            vh.edits_seen = 0
            logger.info("CompletionGate: success claim without verification evidence")
        except Exception as e:
            logger.warning(f"CompletionGate error: {e}")

    def consume_note(self) -> str | None:
        """Return and clear the pending reminder (read by the runtime)."""
        note = self._pending_note
        self._pending_note = None
        return note

    @staticmethod
    def _final_assistant_text(agent) -> str:
        """Extract the text of the last assistant message."""
        for msg in reversed(getattr(agent, "messages", []) or []):
            if msg.get("role") != "assistant":
                continue
            parts = [
                block.get("text", "")
                for block in msg.get("content", []) or []
                if isinstance(block, dict) and "text" in block
            ]
            return "\n".join(p for p in parts if p)
        return ""
