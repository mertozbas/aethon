"""Security hook provider.

Filters tool calls based on security policies:
- Blocks dangerous shell commands
- Restricts file access to workspace
- Enforces commit hygiene (no catch-all git staging) and blocks .bak noise
- Logs network operations
"""

import logging
import re
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

    # Commit hygiene (Phase 8 / R15): catch-all staging bundles unrelated
    # concerns (and stray files) into commits — require explicit paths.
    # Word-aware regexes, not substring checks: 'git commit --amend' must
    # NOT match the -a flag.
    GIT_CATCHALL_PATTERNS = [
        re.compile(r"\bgit\s+add\s+(?:[^|;&]*\s)?(?:-A\b|--all\b|\.(?=\s|;|&|$))"),
        re.compile(r"\bgit\s+commit\s+[^|;&]*(?:(?<![\w-])-a(?:m)?\b|--all\b)"),
    ]
    GIT_ADD_BAK_PATTERN = re.compile(r"\bgit\s+add\b[^|;&]*\.bak\b")

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
        runtime_tools=None,
    ):
        self.workspace = str(Path(workspace).expanduser().resolve())
        # When True, file tools are confined to the workspace. When False (default),
        # they may touch anything under $HOME except the BLOCKED_PATHS list.
        self.workspace_only = workspace_only
        # Optional MacOSConfig — when present, gates disabled use_mac action groups.
        self.macos = macos
        # Optional RuntimeToolsConfig — gates manage_tools dangerous actions.
        self.runtime_tools = runtime_tools
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
                # 1b. Commit hygiene (R15): no catch-all staging/committing.
                for pattern in self.GIT_CATCHALL_PATTERNS:
                    if pattern.search(command):
                        event.cancel_tool = (
                            "BLOCKED: catch-all git staging (git add . / -A / "
                            "--all, git commit -a) is forbidden — stage "
                            "explicit paths so commits stay atomic and "
                            "reviewable."
                        )
                        logger.warning(f"BLOCKED GIT CATCH-ALL: {command}")
                        return
                if self.GIT_ADD_BAK_PATTERN.search(command):
                    event.cancel_tool = (
                        "BLOCKED: do not stage editor backup files (*.bak) — "
                        "they are noise, not source."
                    )
                    logger.warning(f"BLOCKED .bak STAGING: {command}")
                    return

        # 2. File access outside workspace
        if tool_name in ("file_read", "file_write", "editor"):
            path = (
                tool_input.get("path", "")
                or tool_input.get("file_path", "")
                or tool_input.get("command", "")
            )
            # 2a. .bak writes (R15): AETHON keeps its own session history;
            # backup sidecars only pollute workspaces and commits.
            if (
                tool_name in ("file_write", "editor")
                and isinstance(path, str)
                and path.strip().endswith(".bak")
            ):
                event.cancel_tool = (
                    "BLOCKED: writing *.bak files is forbidden (editor backup "
                    "noise). Edit the real file; session history already "
                    "preserves prior versions."
                )
                logger.warning(f"BLOCKED .bak WRITE: {path}")
                return
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
            # Normalize so the gate matches regardless of case/whitespace, even if
            # the tool's dispatch is ever made case-insensitive (defense in depth).
            action = str(tool_input.get("action", "")).strip().lower()
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

        # 5. Dynamic tool loading — gate manage_tools dangerous actions.
        if tool_name == "manage_tools" and self.runtime_tools is not None:
            action = str(tool_input.get("action", "")).strip().lower()
            # Enforce `enabled` here too, decoupling the block from registration
            # (robust even if the tool is ever registered unconditionally).
            if action in ("create", "fetch", "add", "reload") and not getattr(
                self.runtime_tools, "enabled", False
            ):
                event.cancel_tool = (
                    "BLOCKED: dynamic tool loading is disabled. Set "
                    "runtime_tools.enabled=true to enable."
                )
                logger.warning(f"BLOCKED TOOL: manage_tools {action}")
                return
            if action in ("create", "fetch") and not getattr(
                self.runtime_tools, "allow_create", False
            ):
                event.cancel_tool = (
                    "BLOCKED: dynamic tool creation is disabled. Set "
                    "runtime_tools.allow_create=true to enable (the sandbox "
                    "validates code before loading)."
                )
                logger.warning(f"BLOCKED TOOL: manage_tools {action}")
                return
            if action in ("add", "reload") and not getattr(
                self.runtime_tools, "allow_install", False
            ):
                event.cancel_tool = (
                    "BLOCKED: dynamic tool install/reload is disabled. Set "
                    "runtime_tools.allow_install=true to enable."
                )
                logger.warning(f"BLOCKED TOOL: manage_tools {action}")
                return

        # 6. Computer automation — log every action (input-injection audit trail).
        if tool_name == "use_computer":
            logger.info(f"COMPUTER: use_computer {tool_input.get('action', '')}")

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
        """Log tool execution results.

        Errors log the tool input and error text — a bare OK/ERROR hid real
        failures (e.g. a pydantic rejection swallowed behind a bare except).
        """
        tool_name = event.tool_use["name"]
        if event.result.get("status") == "error":
            tool_input = str(event.tool_use.get("input", ""))[:200]
            error_text = " ".join(
                str(block.get("text", ""))
                for block in event.result.get("content", []) or []
                if isinstance(block, dict)
            ).strip()[:500]
            logger.warning(
                f"TOOL: {tool_name} | STATUS: ERROR | "
                f"INPUT: {tool_input} | ERROR: {error_text}"
            )
        else:
            logger.info(f"TOOL: {tool_name} | STATUS: OK")
