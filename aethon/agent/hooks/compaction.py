"""Message-history compaction (Phase 10 E2).

The dominant variable token cost in a long session is finished tool outputs (a
400-line file read five turns ago) riding along in the model's input every turn.
This hook replaces old, large tool-result *texts* with a compact marker — keeping
the toolUse/toolResult structure intact — so the model still knows the tool ran
but no longer carries its bulk.

Two properties make it safe:

* **Compact in batches.** Editing an old message invalidates the provider's
  message cache for everything after it, so compacting a little every turn would
  fight the cache (and E1). We only run a pass once enough old bulk has piled up,
  then leave it stable — the cache is disturbed rarely, not continuously.
* **Compact once, never re-churn.** A compacted result carries a sentinel and is
  skipped forever after, so a stable compacted prefix stays byte-stable.

Invariants: the most recent N turns (including the active one) are never touched;
toolUse/toolResult pairing is preserved (only the result text is rewritten, never
removed); thinking / redacted_thinking blocks are left bit-for-bit (Claude/Bedrock
require it). Advisory — a compaction failure never breaks a turn.
"""

from __future__ import annotations

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeModelCallEvent

from aethon.tools.manage_messages import _parse_turns

logger = logging.getLogger("aethon.compaction")

# Marker placed on a compacted result — also the compact-once-stable sentinel.
_SENTINEL = "⟦sıkıştırıldı⟧"


def _compactable(messages: list, boundary: int, min_chars: int):
    """Yield (content_block, text) for old, large, not-yet-compacted tool results
    in ``messages[:boundary]``, skipping any message that carries a thinking
    block (those must stay bit-for-bit)."""
    for msg in messages[:boundary]:
        content = msg.get("content", []) if isinstance(msg, dict) else []
        if any(
            isinstance(b, dict) and ("thinking" in b or "redacted_thinking" in b)
            for b in content
        ):
            continue
        for block in content:
            tr = block.get("toolResult") if isinstance(block, dict) else None
            if not isinstance(tr, dict):
                continue
            for cb in tr.get("content", []):
                if not isinstance(cb, dict):
                    continue
                text = cb.get("text")
                if not isinstance(text, str) or text.startswith(_SENTINEL):
                    continue
                if len(text) >= min_chars:
                    yield cb, text


def compact_messages(
    messages: list,
    *,
    keep_last_n_turns: int,
    min_chars: int,
    trigger_chars: int,
) -> int:
    """Replace old, large tool-result texts with a compact marker, in one batch
    pass. Returns the number of results compacted (0 = nothing done).

    Runs only when the accumulated compactable bulk exceeds ``trigger_chars`` —
    so the provider message cache is disturbed rarely. The last
    ``keep_last_n_turns`` turns are left untouched.
    """
    if not messages:
        return 0
    turns = _parse_turns(messages)
    if len(turns) <= keep_last_n_turns:
        return 0
    boundary = turns[len(turns) - keep_last_n_turns][0]  # start of the first kept turn

    candidates = list(_compactable(messages, boundary, min_chars))
    if sum(len(text) for _, text in candidates) < trigger_chars:
        return 0  # not enough old bulk to justify breaking the message cache

    for cb, text in candidates:
        cb["text"] = (
            f"{_SENTINEL} önceki tool çıktısı ({len(text)} karakter) yer açmak "
            f"için sıkıştırıldı; gerekirse aracı yeniden çağır."
        )
    return len(candidates)


class CompactionHookProvider(HookProvider):
    """Continuously trims old tool outputs out of the model's input (E2)."""

    def __init__(
        self,
        keep_last_n_turns: int = 4,
        min_chars: int = 800,
        trigger_chars: int = 16000,
    ):
        self._keep = max(1, int(keep_last_n_turns))
        self._min = max(1, int(min_chars))
        self._trigger = max(1, int(trigger_chars))

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeModelCallEvent, self._on_before_model)

    def _on_before_model(self, event: BeforeModelCallEvent) -> None:
        try:
            n = compact_messages(
                event.agent.messages,
                keep_last_n_turns=self._keep,
                min_chars=self._min,
                trigger_chars=self._trigger,
            )
            if n:
                logger.debug(f"Compacted {n} old tool result(s) out of the model input.")
        except Exception as e:
            # Advisory — never let compaction break a turn.
            logger.debug(f"Compaction skipped: {type(e).__name__}: {e}")
