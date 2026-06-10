"""Tool-input validator hook (Phase 8 / R16).

Catches obviously-invalid tool calls BEFORE they reach the tool and turns
opaque downstream errors ("1 validation error for ... command field
required") into self-describing cancellations the agent can immediately act
on. Stops the empty-call → opaque-error → empty-call loops that burned whole
turns in the audit.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent

logger = logging.getLogger("aethon.input_validator")


class InputValidatorHookProvider(HookProvider):
    """Cancel malformed tool calls with a self-describing reason."""

    # tool name -> required non-empty string fields (any one of the tuple).
    REQUIRED_FIELDS = {
        "shell": (("command",),),
        "file_read": (("path", "file_path"),),
        "file_write": (("path", "file_path"),),
        "editor": (("path", "file_path"),),
        "send_message": (("channel",), ("text",)),
    }

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.validate_input)

    def validate_input(self, event: BeforeToolCallEvent) -> None:
        if getattr(event, "cancel_tool", None):
            return  # an earlier hook already cancelled — keep its reason
        tool_name = str(event.tool_use.get("name", ""))
        requirements = self.REQUIRED_FIELDS.get(tool_name)
        if not requirements:
            return
        tool_input = event.tool_use.get("input", {}) or {}
        if not isinstance(tool_input, dict):
            return  # malformed shape — let the tool layer report it

        for alternatives in requirements:
            if any(str(tool_input.get(f, "") or "").strip() for f in alternatives):
                continue
            field_desc = " or ".join(f"'{f}'" for f in alternatives)
            event.cancel_tool = (
                f"INVALID CALL: {tool_name} requires a non-empty {field_desc} "
                f"argument. Re-issue the call with the missing argument filled "
                f"in."
            )
            logger.warning(
                f"Invalid tool call cancelled: {tool_name} missing {field_desc}"
            )
            return
