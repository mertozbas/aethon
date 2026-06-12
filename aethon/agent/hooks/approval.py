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

    # apple_notes actions that mutate (gated); the rest are read-only.
    APPLE_NOTES_WRITE_ACTIONS = {"create", "edit", "append", "delete", "move"}
    # manage_tools actions that load/execute code (gated); others auto-approve.
    MANAGE_TOOLS_DANGEROUS = {"create", "fetch", "add", "reload"}
    # use_computer actions that move the mouse / type / switch apps (gated). The
    # read-only actions (mouse_position, screenshot, screen_size, get_system_info)
    # auto-approve.
    COMPUTER_SENSITIVE_ACTIONS = {
        "click", "double_click", "right_click", "middle_click", "drag", "type",
        "key_press", "hotkey", "scroll", "move_mouse", "switch_app",
        "minimize_all", "show_desktop", "mission_control",
    }

    def __init__(self, requires_approval: list[str] | None = None, macos=None, computer=None):
        self.requires_approval = set(
            requires_approval or ["shell", "file_write", "manage_tools"]
        )
        # Optional MacOSConfig — narrows use_mac approval to its sensitive actions.
        self.macos = macos
        # Optional ComputerCapability — present when use_computer needs approval.
        self.computer = computer

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check_approval)

    def check_approval(self, event: BeforeToolCallEvent) -> None:
        """Request approval for dangerous tool calls via interrupt."""
        tool_name = event.tool_use["name"]

        if tool_name not in self.requires_approval:
            return

        tool_input = event.tool_use.get("input", {})

        # Action-aware refinements — read-only operations auto-approve even when
        # the tool is on the requires_approval list.
        # GitHub GraphQL: only gate mutations (writes).
        if tool_name == "use_github" and not self._is_github_mutation(tool_input):
            return
        # use_mac: when MacOSConfig is present, only its listed sensitive actions
        # (e.g. mail.send, messages.send, keychain.set) need approval.
        if tool_name == "use_mac" and self.macos is not None:
            action = str(tool_input.get("action", "")).strip().lower()
            sensitive = {
                str(s).strip().lower()
                for s in (getattr(self.macos, "actions_requiring_approval", []) or [])
            }
            if action not in sensitive:
                return
        # apple_notes: only mutating actions need approval.
        if (
            tool_name == "apple_notes"
            and str(tool_input.get("action", "")).strip().lower()
            not in self.APPLE_NOTES_WRITE_ACTIONS
        ):
            return
        # manage_tools: only code-loading actions need approval; list/discover/
        # sandbox/remove are safe.
        if (
            tool_name == "manage_tools"
            and str(tool_input.get("action", "")).strip().lower()
            not in self.MANAGE_TOOLS_DANGEROUS
        ):
            return
        # use_computer: only mouse/keyboard/app actions need approval; read-only
        # introspection (screenshot, mouse_position, …) auto-approves.
        if (
            tool_name == "use_computer"
            and str(tool_input.get("action", "")).strip().lower()
            not in self.COMPUTER_SENSITIVE_ACTIONS
        ):
            return

        logger.info(f"Onay isteniyor: {tool_name}")

        # First pass RAISES InterruptException (pausing the turn); on resume the
        # same call RETURNS the user's decision dict. The runtime resolves the
        # decision via the originating channel (S6) and resumes the agent.
        decision = event.interrupt(
            name=f"{tool_name}_approval",
            reason={
                "tool": tool_name,
                "parameters": tool_input,
                "message": f"'{tool_name}' calistirilmak isteniyor. Onayla?",
            },
        )

        # Resume path: cancel the tool unless explicitly approved. Without this
        # the interrupt would be raised but never enforced (the F6 half-wiring).
        if not (isinstance(decision, dict) and decision.get("approved")):
            reason = ""
            if isinstance(decision, dict):
                reason = str(decision.get("reason") or "")
            event.cancel_tool = reason or f"'{tool_name}' onaylanmadı."

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
