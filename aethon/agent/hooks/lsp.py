"""LSP diagnostics hook.

Fires after file-modifying tools (shell/editor/write/edit/file_write) complete,
refreshes any running language servers for the touched files, and appends a
concise diagnostics summary to the tool result so the agent can self-correct.
Read-only and non-destructive. Opt-in via ``lsp.enabled`` + ``lsp.auto_diagnostics``.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent

from aethon.tools.lsp_tool import (
    LSP_SERVERS,
    _detect_language,
    _format_diagnostic,
    _path_to_uri,
    _refresh_document,
)

logger = logging.getLogger("aethon.lsp")


class LSPDiagnosticsHookProvider(HookProvider):
    """Append LSP diagnostics to file-modifying tool results (self-correction)."""

    FILE_TOOLS = {"shell", "editor", "write", "edit", "file_write"}

    def __init__(self, config=None, workspace: str | None = None, max_per_file: int = 10):
        self.config = config
        # Only surface diagnostics for files under the user's home (AETHON's default
        # file boundary) — prevents spamming diagnostics for system files.
        self._home = str(Path.home().resolve())
        self.max_per_file = max_per_file

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._on_tool_complete)

    def _on_tool_complete(self, event: AfterToolCallEvent) -> None:
        tool_name = str(event.tool_use.get("name", "")).lower()
        if tool_name not in self.FILE_TOOLS:
            return
        if not LSP_SERVERS:
            return

        file_paths = [
            fp for fp in self._extract_file_paths(event.tool_use) if self._within_home(fp)
        ]

        diag_summary: list[str] = []
        for fp in file_paths:
            lang = _detect_language(fp)
            if lang and lang in LSP_SERVERS and LSP_SERVERS[lang].get("running"):
                _refresh_document(lang, fp)
                time.sleep(0.5)
                uri = _path_to_uri(fp)
                diags = LSP_SERVERS[lang]["diagnostics"].get(uri, [])
                errors = [d for d in diags if d.get("severity") == 1]
                warnings = [d for d in diags if d.get("severity") == 2]
                if errors or warnings:
                    diag_summary.append(
                        f"{fp}: {len(errors)} error(s), {len(warnings)} warning(s)"
                    )
                    for d in errors[: self.max_per_file]:
                        diag_summary.append(_format_diagnostic(d))

        if diag_summary:
            try:
                existing = event.result.get("content", [])
                existing.append(
                    {"text": "\n[LSP Diagnostics]\n" + "\n".join(diag_summary)}
                )
                event.result["content"] = existing
            except Exception:
                pass

    def _within_home(self, fp: str) -> bool:
        try:
            return str(Path(fp).resolve()).startswith(self._home)
        except Exception:
            return False

    @staticmethod
    def _extract_file_paths(tool_use: dict) -> list[str]:
        """Extract existing file paths from a tool_use input dict."""
        paths: list[str] = []
        tool_input = tool_use.get("input", {})

        for key in ("file_path", "path", "filename", "file", "filepath"):
            val = tool_input.get(key, "")
            if val and isinstance(val, str) and os.path.isfile(val):
                paths.append(val)

        cmd = tool_input.get("command", "")
        if cmd and isinstance(cmd, str):
            for token in cmd.split():
                token = token.strip("\"'")
                if os.path.isfile(token) and _detect_language(token):
                    paths.append(token)

        return list(set(paths))
