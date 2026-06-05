"""System prompt composer.

Builds layered system prompts from workspace files:
SOUL.md + TOOLS.md + CONTEXT.md + SOP list + session info + timestamp.
"""

from pathlib import Path
from datetime import datetime


class SystemPromptComposer:
    """Compose layered system prompts from workspace files."""

    def __init__(self, workspace_dir: str):
        self.workspace = Path(workspace_dir).expanduser()

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

        # 2. TOOLS.md — User preferences
        tools_path = self.workspace / "TOOLS.md"
        if tools_path.exists():
            layers.append(f"## User Preferences\n{tools_path.read_text(encoding='utf-8')}")

        # 3. CONTEXT.md — Current context
        context_path = self.workspace / "CONTEXT.md"
        if context_path.exists():
            layers.append(f"## Current Context\n{context_path.read_text(encoding='utf-8')}")

        # 4. SOP list (built-in + workspace)
        sop_names = []
        try:
            from strands_agents_sops import code_assist, pdd, codebase_summary
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

        # 5. Agent delegation instructions
        layers.append(
            "## Agent Delegation\n"
            "For complex tasks, use the specialist agents:\n"
            "- ask_coder: Coding tasks (writing code, testing, debugging)\n"
            "- ask_researcher: Research tasks (web search, documentation)\n"
            "- ask_analyst: Analysis tasks (data analysis, reporting)\n"
            "- ask_planner: Planning tasks (breaking down work, prioritization)\n"
            "Handle simple tasks yourself. For complex tasks, delegate to the right specialist."
        )

        # 6. Session info
        if session_id:
            layers.append(f"## Active Session\n{session_id}")

        # 6. Timestamp
        layers.append(f"## Time\n{datetime.now().isoformat()}")

        return "\n\n---\n\n".join(layers)
