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
            layers.append(f"## Kisilik\n{soul_path.read_text(encoding='utf-8')}")

        # 2. TOOLS.md — User preferences
        tools_path = self.workspace / "TOOLS.md"
        if tools_path.exists():
            layers.append(f"## Kullanici Tercihleri\n{tools_path.read_text(encoding='utf-8')}")

        # 3. CONTEXT.md — Current context
        context_path = self.workspace / "CONTEXT.md"
        if context_path.exists():
            layers.append(f"## Mevcut Baglam\n{context_path.read_text(encoding='utf-8')}")

        # 4. SOP list (if available)
        sops_dir = self.workspace / "sops"
        if sops_dir.exists():
            sop_names = [f.stem.removesuffix(".sop") for f in sops_dir.glob("*.sop.md")]
            if sop_names:
                sop_list = "\n".join(f"- /{name}" for name in sop_names)
                layers.append(f"## Kullanilabilir Komutlar\n{sop_list}")

        # 5. Session info
        if session_id:
            layers.append(f"## Aktif Session\n{session_id}")

        # 6. Timestamp
        layers.append(f"## Zaman\n{datetime.now().isoformat()}")

        return "\n\n---\n\n".join(layers)
