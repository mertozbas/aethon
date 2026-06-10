"""Post-edit verification hook (Phase 8 / R7).

Runs the configured verify command (lint/type/test) on files the agent just
modified and appends a ``[Verify] PASS/FAIL`` block to the tool result — the
same advisory pattern as the LSP diagnostics hook. This exercises the real
config path that unit suites can miss, and gives the CompletionGate (R6)
concrete evidence that a "done" claim was actually verified.

Advisory by default: feedback is appended, nothing is blocked. With
``reliability.strict`` a FAIL also marks the tool result as ``error`` so the
agent must address it before claiming success.
"""

import logging
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterToolCallEvent

from aethon.agent.hooks.lsp import LSPDiagnosticsHookProvider

logger = logging.getLogger("aethon.verify")

FILE_TOOLS = LSPDiagnosticsHookProvider.FILE_TOOLS

# Tail of the verify output appended on FAIL (keep tool results compact).
_MAX_OUTPUT_CHARS = 800


class PostEditVerifyHookProvider(HookProvider):
    """Run a verify command after file edits; append PASS/FAIL to the result."""

    def __init__(self, config, workspace: str | None = None):
        self.config = config  # ReliabilityConfig
        self._home = str(Path.home().resolve())
        # Evidence for the CompletionGate (R6): outcome of the latest verify
        # run and whether any edits happened since the last verified claim.
        self.last_outcome: str | None = None  # "pass" | "fail" | None
        self.last_detail: str = ""
        self.edits_seen = 0

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self._on_tool_complete)

    def _on_tool_complete(self, event: AfterToolCallEvent) -> None:
        tool_name = str(event.tool_use.get("name", "")).lower()
        if tool_name not in FILE_TOOLS:
            return
        if event.result.get("status") == "error":
            return  # the edit itself failed; nothing to verify

        paths = [
            fp
            for fp in LSPDiagnosticsHookProvider._extract_file_paths(event.tool_use)
            if self._within_home(fp)
        ]
        if not paths:
            return

        # Edits happened — a later success claim needs evidence even when no
        # verify command is available (last_outcome stays None → flagged).
        self.edits_seen += 1

        cmd = self._build_command(paths)
        if cmd is None:
            return

        try:
            proc = subprocess.run(
                cmd,
                shell=isinstance(cmd, str),
                capture_output=True,
                text=True,
                timeout=max(1, int(getattr(self.config, "verify_timeout", 30))),
                cwd=self._project_root(paths[0]),
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"Verify timed out: {cmd}")
            self._append(event, f"\n[Verify] TIMEOUT: {self._display(cmd)}")
            self.last_outcome = None
            return
        except Exception as e:
            logger.warning(f"Verify run failed ({cmd}): {e}")
            self.last_outcome = None
            return

        ok = proc.returncode == 0
        self.last_outcome = "pass" if ok else "fail"
        if ok:
            self.last_detail = ""
            self._append(event, f"\n[Verify] PASS: {self._display(cmd)}")
            return

        output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        self.last_detail = output[-_MAX_OUTPUT_CHARS:]
        self._append(
            event,
            f"\n[Verify] FAIL (exit {proc.returncode}): {self._display(cmd)}\n"
            f"{self.last_detail}",
        )
        if getattr(self.config, "strict", False):
            event.result["status"] = "error"

    def _build_command(self, paths: list[str]):
        """Resolve the verify command for the edited paths.

        Configured ``verify_cmd`` wins ({paths} placeholder substituted, run
        through the shell). Empty config auto-detects: ``ruff check`` on the
        edited Python files when ruff is on PATH, otherwise None (skip).
        """
        template = (getattr(self.config, "verify_cmd", "") or "").strip()
        if template:
            if "{paths}" in template:
                return template.replace("{paths}", shlex.join(paths))
            return template
        py_paths = [p for p in paths if p.endswith(".py")]
        if py_paths and shutil.which("ruff"):
            return ["ruff", "check", *py_paths]
        return None

    @staticmethod
    def _display(cmd) -> str:
        return cmd if isinstance(cmd, str) else shlex.join(cmd)

    @staticmethod
    def _project_root(path: str) -> str:
        """Walk up to the nearest pyproject.toml/.git; fall back to the file's dir."""
        p = Path(path).resolve().parent
        for candidate in (p, *p.parents):
            if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
                return str(candidate)
        return str(p)

    @staticmethod
    def _append(event: AfterToolCallEvent, text: str) -> None:
        try:
            existing = event.result.get("content", []) or []
            existing.append({"text": text})
            event.result["content"] = existing
        except Exception as e:
            logger.warning(f"Verify feedback append failed: {e}")

    def _within_home(self, fp: str) -> bool:
        try:
            return str(Path(fp).resolve()).startswith(self._home)
        except Exception:
            return False
