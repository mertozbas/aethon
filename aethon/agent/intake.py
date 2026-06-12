"""Intake classification (Phase 10 C1).

A lightweight, advisory chat-vs-work classifier: is this inbound message a
casual exchange, or a unit of work (a project) that should be planned and
tracked? It runs only when ``core_loop.intake_enabled`` is on and is deliberately
biased toward **chat** — misreading a question as a project is the annoying
failure mode the design calls out, so the bar for "work" is high and the user
always has an explicit override either way.

This first cut is a transparent heuristic (no model call on the hot path); a
cheap-tier model classifier can slot in behind the same ``classify_intake``
signature later without touching the wiring.
"""

from __future__ import annotations

import re

# A message must be at least this long to even be considered work — a real
# project request carries substance; short imperatives ("dosyayı sil") are
# ordinary turns the agent handles directly.
MIN_WORK_CHARS = 40

# Strong project/creation signals (TR + EN). A work verb is necessary but not
# sufficient — it must pair with length and a non-question to clear the bar.
#
# Single tokens are matched as WHOLE WORDS (both boundaries): Turkish is
# agglutinative, so a prefix match would fire "yap" on "yaptım" (past tense) or
# "yaz" on "yazık". Deliberately conservative — the most ambiguous bare stems
# ("yaz" = write/summer) are left out; the explicit override covers the misses.
_WORD_SIGNALS = (
    "yap", "oluştur", "olustur", "geliştir", "gelistir", "kur", "inşa", "insa",
    "uygula", "tasarla", "kodla", "hazırla", "hazirla", "entegre",
    "build", "implement", "create", "develop", "design", "refactor",
    "migrate", "integrate", "scaffold",
)
# Multiword signals matched as plain substrings.
_PHRASE_SIGNALS = ("set up", "write a", "write an", "build a", "create a")

# Pre-compiled whole-word matcher (Unicode \b is Turkish-letter aware).
_WORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(s) for s in _WORD_SIGNALS) + r")\b"
)


def _has_work_signal(low: str) -> bool:
    if any(sig in low for sig in _PHRASE_SIGNALS):
        return True
    return _WORD_RE.search(low) is not None


def classify_intake(
    text: str,
    *,
    work_phrases: list[str] | tuple[str, ...] = (),
    chat_phrases: list[str] | tuple[str, ...] = (),
) -> str:
    """Classify a message as ``"work"`` or ``"chat"`` (advisory).

    Order: explicit overrides win (chat first, so "just a question, but build…"
    stays chat); then a high bar — a question or a short message is chat; only a
    substantial message carrying a project/creation signal is work.
    """
    t = (text or "").strip()
    low = t.lower()

    for phrase in chat_phrases:
        if phrase and phrase.lower() in low:
            return "chat"
    for phrase in work_phrases:
        if phrase and phrase.lower() in low:
            return "work"

    if not t or t.endswith("?") or len(t) < MIN_WORK_CHARS:
        return "chat"
    if _has_work_signal(low):
        return "work"
    return "chat"
