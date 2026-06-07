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

    # use_mac action prefix -> the MacOSConfig flag that must be enabled for it.
    MACOS_ACTION_GATES = {
        "calendar.": "enable_calendar",
        "reminders.": "enable_reminders",
        "mail.": "enable_mail",
        "shortcuts.": "enable_shortcuts",
        "messages.": "enable_messages",
        "keychain.": "enable_keychain",
    }

    def __init__(
        self,
        workspace: str,
        blocked_commands: list[str] | None = None,
        workspace_only: bool = False,
        macos=None,
    ):
        self.workspace = str(Path(workspace).expanduser().resolve())
        # When True, file tools are confined to the workspace. When False (default),
        # they may touch anything under $HOME except the BLOCKED_PATHS list.
        self.workspace_only = workspace_only
        # Optional MacOSConfig — when present, gates disabled use_mac action groups.
        self.macos = macos
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
                            f"BLOCKED: a command containing '{blocked}' is "
                            f"forbidden by the security policy."
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
                allowed_root = self.workspace if self.workspace_only else str(Path.home())
                event.cancel_tool = (
                    f"BLOCKED: file access outside the allowed area ({path}). "
                    f"Allowed root: {allowed_root} (system and credential paths are always off-limits)."
                )
                logger.warning(f"BLOCKED PATH: {path}")
                return

        # 3. Log network operations (auth material is always redacted)
        if tool_name == "http_request":
            url = tool_input.get("url", "")
            logger.info(f"NETWORK: {tool_name} -> {url}")
        elif tool_name == "scraper":
            # Log the scrape target URL (mirrors http_request logging). No blocking.
            url = tool_input.get("url", "")
            action = tool_input.get("action", "")
            logger.info(f"NETWORK: scraper {action} -> {url}")
        elif tool_name == "use_github":
            # GitHub GraphQL — the token comes from $GITHUB_TOKEN (never in tool_input);
            # log the operation with the token redacted.
            query_type = tool_input.get("query_type", "?")
            logger.info(
                f"NETWORK: use_github -> {query_type} (token=***redacted***)"
            )
        elif tool_name == "jsonrpc":
            # JSON-RPC over HTTP/WS — log endpoint + method, never the auth value.
            endpoint = tool_input.get("endpoint", "")
            method = tool_input.get("method", "")
            logger.info(
                f"NETWORK: jsonrpc -> {endpoint} method={method} "
                f"(auth=***redacted***)"
            )

        # 4. macOS native tool — hard-block disabled action groups, then log
        #    (keychain passwords are never logged).
        if tool_name == "use_mac" and self.macos is not None:
            action = str(tool_input.get("action", ""))
            for prefix, flag in self.MACOS_ACTION_GATES.items():
                if action.startswith(prefix) and not getattr(self.macos, flag, True):
                    event.cancel_tool = (
                        f"BLOCKED: macOS action '{action}' is disabled. "
                        f"Set macos.{flag}=true in config to enable it."
                    )
                    logger.warning(
                        f"BLOCKED macOS ACTION: {action} (macos.{flag} is off)"
                    )
                    return
            if action == "keychain.set":
                logger.info(f"MACOS: use_mac {action} (password=***redacted***)")
            else:
                logger.info(f"MACOS: use_mac {action}")

    def _is_safe_path(self, path: str) -> bool:
        """Check if a path is within allowed boundaries.

        Sensitive system/credential paths are always blocked. The workspace is
        always allowed. Beyond that: ``workspace_only`` confines to the workspace,
        otherwise anything under the home directory is allowed.
        """
        try:
            resolved = Path(path).expanduser().resolve()
            workspace = Path(self.workspace).resolve()
            home = Path.home().resolve()

            # Always block sensitive system/credential paths (highest priority).
            for blocked in self.BLOCKED_PATHS:
                blocked_resolved = Path(blocked).expanduser().resolve()
                if str(resolved).startswith(str(blocked_resolved)):
                    return False

            # Inside the workspace is always allowed.
            if str(resolved).startswith(str(workspace)):
                return True

            # Strict mode: nothing outside the workspace.
            if self.workspace_only:
                return False

            # Default mode: allow anywhere under the home directory.
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
