"""Persistent learning tool.

Lets the agent append discoveries to ``LEARNINGS.md`` in the workspace so they
persist across sessions (the composer reads this file back into the prompt).
"""

from datetime import datetime
from pathlib import Path

from strands import tool


def create_learning_tool(workspace: str):
    """Build a ``record_learning`` tool bound to the given workspace."""
    ws = Path(workspace).expanduser()

    @tool
    def record_learning(category: str, content: str) -> str:
        """Append a learning to LEARNINGS.md so it persists across sessions.

        Use when you discover an important pattern, fix, preference, or fact
        worth remembering in future sessions (not for one-off conversational
        details).

        Args:
            category: Short topic label (e.g. "build", "preference", "gotcha").
            content: The learning itself, in one or a few sentences.

        Returns:
            A short confirmation string.
        """
        path = ws / "LEARNINGS.md"
        stamp = datetime.now().isoformat(timespec="seconds")
        entry = f"\n### {category} ({stamp})\n{content}\n"
        try:
            if path.exists():
                with open(path, "a", encoding="utf-8") as f:
                    f.write(entry)
            else:
                ws.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# Learnings & Discoveries\n")
                    f.write(entry)
            return f"Learning recorded: {category}"
        except Exception as e:
            return f"Failed to record learning: {e}"

    return record_learning
