"""SOP (Structured Operating Procedure) runner.

Loads and executes SOPs from built-in package and workspace directories.
"""

import logging
import re
from pathlib import Path

from strands import Agent


logger = logging.getLogger("aethon.sops")


class SOPRunner:
    """Load and execute SOPs."""

    def __init__(self, sop_directories: list[str], builtin_enabled: bool = True):
        self.sop_dirs = [Path(d).expanduser() for d in sop_directories]
        self._sops: dict[str, str] = {}
        self._load_sops(builtin_enabled)

    def _load_sops(self, builtin_enabled: bool):
        """Load all SOP content."""
        # 1. Built-in SOPs (strands-agents-sops package)
        if builtin_enabled:
            try:
                from strands_agents_sops import code_assist, pdd, codebase_summary

                self._sops["code-assist"] = code_assist
                self._sops["pdd"] = pdd
                self._sops["codebase-summary"] = codebase_summary
                logger.info(f"Dahili SOP'lar yuklendi: {list(self._sops.keys())}")
            except ImportError:
                logger.warning("strands-agents-sops yuklu degil — dahili SOP'lar atlanacak")

        # 2. Custom SOPs (workspace/sops/*.sop.md)
        for sop_dir in self.sop_dirs:
            if not sop_dir.exists():
                continue
            for sop_file in sop_dir.glob("*.sop.md"):
                name = sop_file.stem.removesuffix(".sop")
                self._sops[name] = sop_file.read_text(encoding="utf-8")
                logger.info(f"Ozel SOP yuklendi: {name}")

    def list_sops(self) -> list[dict]:
        """List available SOPs with name and description."""
        result = []
        for name, content in self._sops.items():
            match = re.search(
                r"## Overview\s*\n(.*?)(?=\n##|\n#|\Z)", content, re.DOTALL
            )
            description = match.group(1).strip()[:200] if match else ""
            result.append({"name": name, "description": description})
        return result

    def get_sop(self, name: str) -> str | None:
        """Get SOP content by name."""
        return self._sops.get(name)

    def run_sop(self, name: str, agent: Agent, user_input: str = "") -> str:
        """Execute a SOP on the given agent."""
        sop_content = self.get_sop(name)
        if not sop_content:
            return f"SOP bulunamadi: {name}"

        prompt = (
            f'<agent-sop name="{name}">\n'
            f"<content>\n{sop_content}\n</content>\n"
            f"<user-input>\n{user_input}\n</user-input>\n"
            f"</agent-sop>"
        )

        result = agent(prompt)

        try:
            content = result.message["content"]
            texts = [block["text"] for block in content if "text" in block]
            return "\n".join(texts) if texts else str(result)
        except (KeyError, TypeError):
            return str(result)

    def is_sop_command(self, text: str) -> tuple[bool, str, str]:
        """Check if text is a SOP command.

        Returns:
            (is_sop, sop_name, user_input)
        """
        text = text.strip()
        if not text.startswith("/"):
            return False, "", ""

        parts = text.split(maxsplit=1)
        sop_name = parts[0][1:]  # Remove "/"
        user_input = parts[1] if len(parts) > 1 else ""

        if sop_name in self._sops:
            return True, sop_name, user_input

        return False, "", ""
