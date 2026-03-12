"""CONTEXT.md automatic updater.

Key-value based context management using ### Key\\nValue format.
"""

import re
from pathlib import Path


class ContextUpdater:
    """Manage CONTEXT.md sections with key-value format."""

    def __init__(self, workspace_dir: str):
        self.context_file = Path(workspace_dir).expanduser() / "CONTEXT.md"

    def update(self, key: str, value: str) -> str:
        """Add or update a context section.

        Args:
            key: Section key (becomes ### heading).
            value: Section content.

        Returns:
            Confirmation message.
        """
        content = ""
        if self.context_file.exists():
            content = self.context_file.read_text(encoding="utf-8")

        replacement = f"### {key}\n{value}"
        pattern = rf"### {re.escape(key)}\n.*?(?=\n### |\Z)"

        if re.search(pattern, content, re.DOTALL | re.MULTILINE):
            content = re.sub(
                pattern, replacement, content,
                count=1, flags=re.DOTALL | re.MULTILINE,
            )
        else:
            content = content.rstrip() + f"\n\n{replacement}\n"

        self.context_file.write_text(content, encoding="utf-8")
        return f"CONTEXT.md guncellendi: {key}"

    def get(self, key: str) -> str | None:
        """Read a context section value.

        Args:
            key: Section key to read.

        Returns:
            Section content or None if not found.
        """
        if not self.context_file.exists():
            return None
        content = self.context_file.read_text(encoding="utf-8")
        pattern = rf"### {re.escape(key)}\n(.*?)(?=\n### |\Z)"
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        return match.group(1).strip() if match else None

    def list_keys(self) -> list[str]:
        """List all context section keys.

        Returns:
            List of key names.
        """
        if not self.context_file.exists():
            return []
        content = self.context_file.read_text(encoding="utf-8")
        return re.findall(r"^### (.+)$", content, re.MULTILINE)
