"""Security hook provider.

Filters tool calls based on security policies:
- Blocks dangerous shell commands
- Restricts file access to workspace
- Logs network operations
"""

import logging
from pathlib import Path
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import BeforeToolCallEvent, AfterToolCallEvent


logger = logging.getLogger("aethon.security")


class SecurityHookProvider(HookProvider):
    """Filter tool calls based on security policies."""

    BLOCKED_COMMANDS = [
        "rm -rf /", "rm -rf ~", "rm -rf /*",
        "sudo ", "su ",
        "mkfs", "dd if=",
        "chmod 777",
        "> /dev/sda",
        "| sh", "| bash",
        "curl | sh", "wget | sh",
        "kill -9 1",
    ]

    BLOCKED_PATHS = [
        "/etc/", "/usr/", "/bin/", "/sbin/",
        "/System/", "/Library/",
        "~/.ssh/", "~/.gnupg/",
        "~/.aethon/credentials/",
    ]

    def __init__(self, workspace: str, blocked_commands: list[str] | None = None):
        self.workspace = str(Path(workspace).expanduser().resolve())
        if blocked_commands:
            self.BLOCKED_COMMANDS = self.BLOCKED_COMMANDS + blocked_commands

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check_tool_safety)
        registry.add_callback(AfterToolCallEvent, self.log_tool_result)

    def check_tool_safety(self, event: BeforeToolCallEvent) -> None:
        """Check tool call against security policies."""
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # 1. Dangerous command check
        if tool_name == "shell":
            command = tool_input.get("command", "")
            if isinstance(command, str):
                for blocked in self.BLOCKED_COMMANDS:
                    if blocked in command:
                        event.cancel_tool = (
                            f"ENGELLENDI: '{blocked}' iceren komut guvenlik "
                            f"politikasi tarafindan yasaklandi."
                        )
                        logger.warning(f"BLOCKED COMMAND: {command}")
                        return

        # 2. File access outside workspace
        if tool_name in ("file_read", "file_write", "editor"):
            path = (
                tool_input.get("path", "")
                or tool_input.get("file_path", "")
                or tool_input.get("command", "")
            )
            if path and not self._is_safe_path(path):
                event.cancel_tool = (
                    f"ENGELLENDI: Workspace disi dosya erisimi ({path}). "
                    f"Sadece {self.workspace} icindeki dosyalara erisebilirsiniz."
                )
                logger.warning(f"BLOCKED PATH: {path}")
                return

        # 3. Log network operations
        if tool_name == "http_request":
            url = tool_input.get("url", "")
            logger.info(f"NETWORK: {tool_name} -> {url}")

    def _is_safe_path(self, path: str) -> bool:
        """Check if a path is within allowed boundaries."""
        try:
            resolved = Path(path).expanduser().resolve()
            workspace = Path(self.workspace).resolve()
            home = Path.home().resolve()

            # Inside workspace?
            if str(resolved).startswith(str(workspace)):
                return True

            # In blocked paths?
            for blocked in self.BLOCKED_PATHS:
                blocked_resolved = Path(blocked).expanduser().resolve()
                if str(resolved).startswith(str(blocked_resolved)):
                    return False

            # Inside home but outside workspace — allow with caution
            if str(resolved).startswith(str(home)):
                return True

            return False
        except Exception:
            return False

    def log_tool_result(self, event: AfterToolCallEvent) -> None:
        """Log tool execution results."""
        tool_name = event.tool_use["name"]
        status = "ERROR" if event.result.get("status") == "error" else "OK"
        logger.info(f"TOOL: {tool_name} | STATUS: {status}")
