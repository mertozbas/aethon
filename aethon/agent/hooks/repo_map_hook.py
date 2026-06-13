"""Repo-map capture hook (Phase 10 E3).

Watches file_read tool calls and records each read file in the RepoMap, so the
summary (path → purpose/symbols/hash) is available for the prompt's repo-map
layer next time. Advisory — a capture failure never breaks a turn.
"""

from __future__ import annotations

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent

logger = logging.getLogger("aethon.repo_map")


class RepoMapHookProvider(HookProvider):
    def __init__(self, repo_map):
        self._repo_map = repo_map

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._capture)

    def _capture(self, event: AfterToolCallEvent) -> None:
        try:
            if event.tool_use.get("name") != "file_read":
                return
            path = (event.tool_use.get("input") or {}).get("path")
            if not path:
                return
            # file_read accepts a comma-separated list of paths.
            for p in str(path).split(","):
                p = p.strip()
                if p:
                    self._repo_map.observe(p)
        except Exception as e:
            logger.debug(f"Repo-map capture skipped: {type(e).__name__}: {e}")
