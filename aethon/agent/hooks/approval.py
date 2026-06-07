"""Approval hook provider.

Uses Strands Interrupt mechanism to pause agent execution
for human approval on dangerous tool calls.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent


logger = logging.getLogger("aethon.approval")


class ApprovalHookProvider(HookProvider):
    """Interrupt-based approval for dangerous tool calls."""

    def __init__(self, requires_approval: list[str] | None = None):
        self.requires_approval = set(
            requires_approval or ["shell", "file_write"]
        )

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check_approval)

    def check_approval(self, event: BeforeToolCallEvent) -> None:
        """Request approval for dangerous tool calls via interrupt."""
        tool_name = event.tool_use["name"]

        if tool_name not in self.requires_approval:
            return

        tool_input = event.tool_use.get("input", {})

        # Action-aware refinement: GitHub GraphQL reads are safe — only gate
        # mutations (writes). Read-only queries auto-approve even when use_github
        # is on the requires_approval list.
        if tool_name == "use_github" and not self._is_github_mutation(tool_input):
            return

        logger.info(f"Onay isteniyor: {tool_name}")

        event.interrupt(
            name=f"{tool_name}_approval",
            reason={
                "tool": tool_name,
                "parameters": tool_input,
                "message": f"'{tool_name}' calistirilmak isteniyor. Onayla?",
            },
        )

    @staticmethod
    def _is_github_mutation(tool_input: dict) -> bool:
        """True when a use_github call is a mutation (write) vs. a read-only query."""
        if str(tool_input.get("query_type", "")).lower() == "mutation":
            return True
        query = str(tool_input.get("query", ""))
        try:
            from aethon.tools.vendor.use_github import is_mutation_query

            return is_mutation_query(query)
        except Exception:
            return query.lower().strip().startswith("mutation")
