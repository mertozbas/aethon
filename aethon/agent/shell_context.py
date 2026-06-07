"""Shell-history capture for prompt continuity.

Reads the user's bash/zsh history so the agent has lightweight continuity about
what the user has been doing in their terminal. Gated behind
``prompt.include_shell_history`` (off by default for privacy).
"""

from pathlib import Path


def get_shell_histories(max_entries: int = 200) -> dict[str, list[str]]:
    """Parse bash and zsh history files (last ``max_entries`` lines each)."""
    histories: dict[str, list[str]] = {}
    home = Path.home()
    for shell, fname in (("bash", ".bash_history"), ("zsh", ".zsh_history")):
        p = home / fname
        if p.exists():
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    histories[shell] = f.readlines()[-max_entries:]
            except Exception:
                continue
    return histories


def format_shell_context(lines: int = 50) -> str:
    """Render recent shell history as a markdown section, or '' when none."""
    histories = get_shell_histories()
    if not histories:
        return ""
    out = "## Recent Shell History\n"
    for shell, entries in histories.items():
        recent = "".join(entries[-lines:]).strip()
        if recent:
            out += f"\n### {shell.upper()}\n```\n{recent}\n```\n"
    return out
