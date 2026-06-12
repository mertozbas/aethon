"""Capability diet — semantic-ish tool discovery (Phase 10 C6).

Every turn carries the full schema of every loaded tool, and a few tools have
HUGE schemas (use_mac alone is enormous). The diet keeps an always-on core and
loads the heavy, domain-specific tools only when the session looks like it needs
them — shrinking the per-turn fixed tool-schema cost.

Crucially this is decided PER SESSION (at agent-build time), not per turn. In the
Anthropic/OpenAI APIs the tool list is a separate, cached array; changing it every
turn would invalidate the prompt/tool cache on every turn and defeat the whole
prompt-cache win (E1). So the design's "discovered tools in the volatile tail" is
not physically achievable — instead the tool set is chosen once from the message
that builds the agent and stays stable for that agent's lifetime (a later eviction
+ rebuild re-evaluates against the then-current message).

Honest trade-off (opt-in): if the session shifts topic to one whose heavy tool was
pruned, the agent won't have it until it's rebuilt. So the discoverable set is kept
to the genuinely heavy, clearly domain-specific tools, with broad keyword triggers
(err toward including), and the diet is off by default. Keyword matching — not an
embedding call per build — keeps it cheap and provider-independent.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("aethon.capability_diet")

# Heavy / domain-specific tools and the (TR+EN) keywords that pull them into the
# session. Anything NOT listed here is core and always loaded.
DISCOVERABLE_TOOLS: dict[str, tuple[str, ...]] = {
    "use_mac": (
        "mac", "calendar", "takvim", "reminder", "hatırlat", "hatirlat", "mail",
        "e-posta", "eposta", "posta", "contact", "kişi", "kisi", "safari",
        "finder", "shortcut", "kısayol", "kisayol", "music", "müzik", "muzik",
        "keychain", "imessage", "mesaj gönder", "mesaj gonder",
    ),
    "apple_notes": ("apple not", "apple note", "notlarım", "notlarim", "not al"),
    "use_computer": (
        "bilgisayarı kullan", "bilgisayari kullan", "use computer", "screen",
        "ekran görüntüsü", "ekran goruntusu", "fareyi", "mouse", "tıkla", "tikla",
        "click", "klavye", "keyboard", "otomasyon", "automate the",
    ),
    "use_github": (
        "github", "pull request", "pull-request", "issue", "repo", "depo",
        "commit", "branch", "merge",
    ),
    "scraper": (
        "scrape", "kazı", "kazi", "web sayfas", "html", "web sitesi", "website",
        "site içeriğ", "site icerig", "sayfayı çek", "sayfayi cek",
    ),
    "jsonrpc": ("jsonrpc", "json-rpc", "json rpc", "rpc çağrı", "rpc cagri"),
}


def _tool_name(t) -> str:
    return getattr(t, "tool_name", None) or getattr(t, "__name__", "") or ""


def select_tools(tools: list, hint: str) -> list:
    """Return the diet-filtered tool list for a session whose building message is
    ``hint``. Core tools always pass; a discoverable tool passes only if a keyword
    appears in the hint. An empty hint prunes nothing (we can't judge relevance,
    so stay safe and keep everything)."""
    low = (hint or "").lower()
    if not low.strip():
        return tools
    kept, dropped = [], []
    for t in tools:
        triggers = DISCOVERABLE_TOOLS.get(_tool_name(t))
        if triggers is None or any(k in low for k in triggers):
            kept.append(t)
        else:
            dropped.append(_tool_name(t))
    if dropped:
        logger.debug(f"Capability diet pruned {len(dropped)} tool(s): {', '.join(dropped)}")
    return kept
