"""System prompt composer.

Builds layered system prompts from workspace files plus optional awareness
layers (environment, learnings, shell history, recent logs):
SOUL.md + [environment] + TOOLS.md + CONTEXT.md + [LEARNINGS.md] +
[shell history] + [recent logs] + SOP list + delegation + session + timestamp.
"""

import os
import platform
import socket
import sys
from datetime import datetime
from pathlib import Path


class SystemPromptComposer:
    """Compose layered system prompts from workspace files."""

    def __init__(self, workspace_dir: str, config=None, logs_dir: str | None = None):
        """
        Args:
            workspace_dir: Workspace directory (SOUL.md/TOOLS.md/CONTEXT.md/...).
            config: Optional PromptConfig controlling the optional layers.
            logs_dir: Optional directory holding ``aethon.log`` (for the recent-logs layer).
        """
        self.workspace = Path(workspace_dir).expanduser()
        self.config = config
        self.logs_dir = Path(logs_dir).expanduser() if logs_dir else None

    def _flag(self, name: str, default):
        """Read a PromptConfig flag, falling back to a default when no config."""
        return getattr(self.config, name, default) if self.config is not None else default

    def _get_environment_info(self) -> str:
        """Capture the system environment for agent awareness."""
        env = {
            "os": platform.system(),
            "arch": platform.machine(),
            "python": (
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            ),
            "cwd": str(Path.cwd()),
            "home": str(Path.home()),
            "shell": os.environ.get("SHELL", "unknown"),
            "hostname": socket.gethostname(),
        }
        return (
            "## System Environment\n"
            f"- OS: {env['os']} ({env['arch']})\n"
            f"- Python: {env['python']}\n"
            f"- Working Directory: {env['cwd']}\n"
            f"- Home: {env['home']}\n"
            f"- Shell: {env['shell']}\n"
            f"- Hostname: {env['hostname']}\n"
        )

    def _get_recent_logs(self, num_lines: int = 50) -> str:
        """Return the last ``num_lines`` of aethon.log as a markdown block, or ''."""
        if not self.logs_dir:
            return ""
        log_path = self.logs_dir / "aethon.log"
        if not log_path.exists():
            return ""
        try:
            with open(log_path, encoding="utf-8", errors="ignore") as f:
                tail = f.readlines()[-num_lines:]
        except Exception:
            return ""
        body = "".join(tail).strip()
        if not body:
            return ""
        return f"## Recent Activity Logs\n```\n{body}\n```\n"

    def _get_self_awareness(self) -> str:
        """Embed a small, curated set of AETHON's own source files.

        Lets the agent reason about / debug itself. Opt-in (default off) and
        deliberately limited to key files (never a full source dump).
        """
        key_files = ["agent/prompt.py", "agent/runtime.py", "agent/specialists.py"]
        base = Path(__file__).resolve().parent.parent  # the `aethon` package root
        parts = []
        for rel in key_files:
            p = base / rel
            if not p.exists():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if len(text) > 8000:
                text = text[:8000] + "\n... [truncated]"
            parts.append(f"### {rel}\n```python\n{text}\n```")
        if not parts:
            return ""
        return "## Self-Awareness (key source files)\n" + "\n\n".join(parts)

    def compose(self, session_id: str = "") -> str:
        """Build the complete system prompt.

        Args:
            session_id: Current session identifier.

        Returns:
            Combined system prompt string.
        """
        layers = []

        # 1. SOUL.md — Personality
        soul_path = self.workspace / "SOUL.md"
        if soul_path.exists():
            layers.append(f"## Personality\n{soul_path.read_text(encoding='utf-8')}")

        # 2. Environment awareness
        if self._flag("include_environment", True):
            layers.append(self._get_environment_info())

        # 3. TOOLS.md — User preferences
        tools_path = self.workspace / "TOOLS.md"
        if tools_path.exists():
            layers.append(f"## User Preferences\n{tools_path.read_text(encoding='utf-8')}")

        # 4. CONTEXT.md — Current context
        context_path = self.workspace / "CONTEXT.md"
        if context_path.exists():
            layers.append(f"## Current Context\n{context_path.read_text(encoding='utf-8')}")

        # 5. LEARNINGS.md — Persistent learnings
        if self._flag("include_learnings", True):
            learnings_path = self.workspace / "LEARNINGS.md"
            if learnings_path.exists():
                text = learnings_path.read_text(encoding="utf-8").strip()
                if text:
                    layers.append(f"## Learnings\n{text}")

        # 6. Recent shell history (off by default — privacy)
        if self._flag("include_shell_history", False):
            from aethon.agent.shell_context import format_shell_context

            shell_ctx = format_shell_context(self._flag("shell_history_lines", 50))
            if shell_ctx:
                layers.append(shell_ctx)

        # 7. Recent activity logs
        if self._flag("include_recent_logs", True):
            recent_logs = self._get_recent_logs(self._flag("log_lines", 50))
            if recent_logs:
                layers.append(recent_logs)

        # 7.5 Self-awareness (optional; default off; opt-in via flag or env)
        if self._flag("include_self_awareness", False) or os.environ.get(
            "AETHON_SELF_AWARE", ""
        ).lower() == "true":
            self_aware = self._get_self_awareness()
            if self_aware:
                layers.append(self_aware)

        # 8. SOP list (built-in + workspace)
        sop_names = []
        try:
            from strands_agents_sops import code_assist, pdd, codebase_summary  # noqa: F401
            sop_names.extend(["code-assist", "pdd", "codebase-summary"])
        except ImportError:
            pass
        sops_dir = self.workspace / "sops"
        if sops_dir.exists():
            for f in sops_dir.glob("*.sop.md"):
                name = f.stem.removesuffix(".sop")
                if name not in sop_names:
                    sop_names.append(name)
        if sop_names:
            sop_list = "\n".join(f"- /{name}" for name in sop_names)
            layers.append(
                f"## Available SOP Commands\n"
                f"When the user types a command starting with /, an SOP is triggered:\n{sop_list}"
            )

        # 9. Agent delegation instructions
        layers.append(
            "## Agent Delegation\n"
            "For complex tasks, use the specialist agents:\n"
            "- ask_coder: Coding tasks (writing code, testing, debugging)\n"
            "- ask_researcher: Research tasks (web search, documentation)\n"
            "- ask_analyst: Analysis tasks (data analysis, reporting)\n"
            "- ask_planner: Planning tasks (breaking down work, prioritization)\n"
            "Handle simple tasks yourself. For complex tasks, delegate to the right specialist."
        )

        # 10. Session info
        if session_id:
            layers.append(f"## Active Session\n{session_id}")

        # 11. Timestamp
        layers.append(f"## Time\n{datetime.now().isoformat()}")

        return "\n\n---\n\n".join(layers)
