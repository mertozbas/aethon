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

# A message is heuristically "work" only when it pairs a creation/build VERB
# with a project/artifact NOUN — a far higher bar than a verb alone. "build a
# stronger relationship" or "create a memory" carry a generic verb but no
# project object, so they stay chat; "build a CLI tool" / "blog API geliştir"
# clear the bar. The explicit override covers anything the heuristic misses.
#
# Single tokens match as WHOLE WORDS (both Unicode boundaries): Turkish is
# agglutinative, so a prefix match would fire "yap" on "yaptım" or "api" on
# "kapı". The most ambiguous bare stems ("yaz" = write/summer) are left out.
_WORK_VERBS = (
    "yap", "oluştur", "olustur", "geliştir", "gelistir", "kur", "inşa", "insa",
    "uygula", "tasarla", "kodla", "hazırla", "hazirla", "entegre", "set up",
    "build", "implement", "create", "develop", "design", "refactor",
    "migrate", "integrate", "scaffold",
)
_PROJECT_NOUNS = (
    "api", "servis", "service", "uygulama", "app", "application", "sistem",
    "system", "tool", "araç", "arac", "site", "website", "web", "bot",
    "script", "betik", "cli", "kütüphane", "kutuphane", "library", "modül",
    "modul", "module", "endpoint", "veritabanı", "veritabani", "database",
    "pipeline", "entegrasyon", "integration", "dashboard", "panel", "arayüz",
    "arayuz", "interface", "test", "sayfa", "page", "fonksiyon", "function",
    "komut", "command", "proje", "project", "sunucu", "server", "özellik",
    "ozellik", "feature",
)


def _word_re(words):
    return re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b")


# Pre-compiled whole-word matchers (Unicode \b is Turkish-letter aware).
_VERB_RE = _word_re(_WORK_VERBS)
_NOUN_RE = _word_re(_PROJECT_NOUNS)


def _has_work_signal(low: str) -> bool:
    """A creation/build verb AND a project/artifact noun — both, by whole word."""
    return _VERB_RE.search(low) is not None and _NOUN_RE.search(low) is not None


def classify_intake(
    text: str,
    *,
    work_phrases: list[str] | tuple[str, ...] = (),
    chat_phrases: list[str] | tuple[str, ...] = (),
) -> str:
    """Classify a message as ``"work"`` or ``"chat"`` (advisory).

    Order: explicit overrides win (chat first, so "just a question, but build…"
    stays chat); then a high bar — a question or a short message is chat; only a
    substantial message that pairs a project/creation verb with a project noun
    is work.
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
