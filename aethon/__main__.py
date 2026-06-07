"""AETHON CLI entry point."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

from aethon import __version__
from aethon.config import AethonConfig
from aethon.gateway.server import AethonGateway

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="aethon")
def main():
    """AETHON — Personal AI assistant."""
    pass


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config file path")
@click.option("--force", is_flag=True, help="Overwrite an existing config without asking")
def init(config: str, force: bool):
    """Set up AETHON (provider, model, memory) and write the config file."""
    from aethon.setup_wizard import run_wizard

    run_wizard(config, force=force)


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config file path")
def doctor(config: str):
    """Diagnose the current configuration and provider availability."""
    from aethon.agent.model_factory import check_model_availability

    cfg_path = Path(config).expanduser()
    console.print(f"\n[bold cyan]AETHON doctor[/]  (config: {cfg_path})\n")

    if not cfg_path.exists():
        console.print("[yellow]No config file yet — run [bold]aethon init[/].[/]\n")
        return

    cfg = AethonConfig.load(config)
    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model:    [green]{cfg.model.model_id}[/]")

    available, msg = check_model_availability(cfg.model)
    console.print(f"  Provider check: [{'green' if available else 'red'}]{msg}[/]")

    console.print(
        f"  Memory:   [{'green' if cfg.memory.enabled else 'dim'}]"
        f"{'enabled' if cfg.memory.enabled else 'disabled'}[/]"
        f" ({cfg.memory.embedding_provider} embeddings)"
    )
    console.print()


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config file path")
def start(config: str):
    """Start AETHON."""
    if not Path(config).expanduser().exists():
        console.print("[yellow]No config found — let's set up AETHON first.[/]")
        from aethon.setup_wizard import run_wizard

        if run_wizard(config) is None:
            return

    console.print("[bold cyan]AETHON[/] starting...\n")

    cfg = AethonConfig.load(config)

    _ensure_workspace(cfg)

    from aethon.agent.model_factory import check_model_availability

    available, msg = check_model_availability(cfg.model)
    if not available:
        console.print(f"[red]Provider not ready:[/] {msg}")
        console.print("Run [bold]aethon init[/] to reconfigure, or [bold]aethon doctor[/] to diagnose.")
        return

    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model: [green]{cfg.model.model_id}[/]")
    console.print(f"  WebChat: [green]http://127.0.0.1:{cfg.channels.webchat.port}[/]")

    # Embedding model check (for VectorMemory)
    if cfg.memory.enabled:
        _check_embedding_model(cfg)

    # Multi-agent status
    if cfg.multi_agent.enabled:
        console.print("  Multi-Agent: [green]active[/]")
    else:
        console.print("  Multi-Agent: [dim]disabled[/]")

    # SOP status
    if cfg.sops.enabled:
        try:
            from aethon.sops.runner import SOPRunner

            sop_dirs = [str(Path(cfg.paths.workspace).expanduser() / "sops")]
            runner = SOPRunner(sop_dirs, cfg.sops.builtin_sops_enabled)
            sop_count = len(runner.list_sops())
            console.print(f"  SOPs: [green]{sop_count} loaded[/]")
        except Exception:
            console.print("  SOPs: [yellow]failed to load[/]")

    # Scheduler status (the gateway only starts it when SOPs are enabled too)
    if cfg.scheduler.enabled and cfg.sops.enabled:
        console.print("  Scheduler: [green]active[/]")
    elif cfg.scheduler.enabled:
        console.print("  Scheduler: [yellow]disabled (requires SOPs)[/]")
    else:
        console.print("  Scheduler: [dim]disabled[/]")

    # Telemetry status
    if cfg.telemetry.enabled:
        console.print("  Telemetry: [green]active[/]")
    else:
        console.print("  Telemetry: [dim]disabled[/]")

    # Dashboard status
    if cfg.dashboard.enabled and cfg.channels.webchat.enabled:
        console.print(
            f"  Dashboard: [green]http://127.0.0.1:{cfg.channels.webchat.port}/dashboard[/]"
        )

    # Webhook status
    if cfg.webhook.enabled and cfg.channels.webchat.enabled:
        console.print(
            f"  Webhook: [green]http://127.0.0.1:{cfg.channels.webchat.port}/webhook/{{channel}}[/]"
        )

    # MCP status
    if cfg.mcp.enabled:
        console.print(f"  MCP: [green]{len(cfg.mcp.servers)} servers[/]")
    else:
        console.print("  MCP: [dim]disabled[/]")

    # List enabled channels
    _print_channels(cfg)

    console.print()

    gateway = AethonGateway(cfg)
    try:
        asyncio.run(gateway.start())
    except KeyboardInterrupt:
        pass  # Signal handler already triggered graceful shutdown


def _check_embedding_model(config: AethonConfig):
    """Check if embedding model is available."""
    import requests

    emb_provider = getattr(config.memory, "embedding_provider", "ollama")
    emb_model = config.memory.embedding_model

    if emb_provider == "openai":
        emb_key = getattr(config.memory, "embedding_api_key", "")
        if emb_key:
            console.print(f"  Memory: [green]{emb_model}[/] (openai, active)")
        else:
            console.print(f"  Memory: [yellow]{emb_model}[/] (openai, API key missing)")
        return

    # Default: Ollama (use the memory embedding host, not the chat model's host)
    emb_host = getattr(config.memory, "embedding_host", "") or config.model.host
    try:
        r = requests.get(f"{emb_host}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(emb_model in m for m in models):
            console.print(f"  Memory: [green]{emb_model}[/] (ollama, active)")
        else:
            console.print(
                f"  Memory: [yellow]{emb_model} not found[/] — "
                f"ollama pull {emb_model}"
            )
    except Exception:
        console.print("  Memory: [yellow]Ollama connection error[/]")


def _print_channels(config: AethonConfig):
    """Print enabled channels status."""
    channels = []
    if config.channels.cli.enabled:
        channels.append("CLI")
    if config.channels.webchat.enabled:
        channels.append("WebChat")
    if config.channels.telegram.enabled:
        channels.append("Telegram")
    if config.channels.discord.enabled:
        channels.append("Discord")
    if config.channels.slack.enabled:
        channels.append("Slack")
    if config.channels.whatsapp.enabled:
        channels.append("WhatsApp")
    console.print(f"  Channels: [green]{', '.join(channels)}[/]")


def _ensure_workspace(config: AethonConfig):
    """Create workspace directory with default files if not exists."""
    workspace = Path(config.paths.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)

    # Default SOUL.md
    soul = workspace / "SOUL.md"
    if not soul.exists():
        soul.write_text(
            "# AETHON — Soul\n\n"
            "You are AETHON, a personal AI assistant. Your purpose is to make the "
            "user's life easier, get their work done faster, and be a genuine "
            "partner on technical matters.\n\n"
            "## Identity\n\n"
            "- Be pragmatic and direct.\n"
            "- Own your mistakes — don't hide behind excuses.\n"
            "- Say when you don't know — never make things up.\n\n"
            "## Communication\n\n"
            "- You can speak both English and Turkish. Reply in whichever "
            "language the user writes in.\n"
            "- Keep answers short, focused, and clear. Skip needless preamble.\n"
            "- Format your responses in Markdown. Use headings, bold, code "
            "blocks, and lists.\n\n"
            "## Decision Making\n\n"
            "- For simple tasks, just do them — don't ask.\n"
            "- For complex tasks, propose a plan first.\n"
            "- When there are several approaches, pick the simplest one.\n",
            encoding="utf-8",
        )

    # Default TOOLS.md
    tools = workspace / "TOOLS.md"
    if not tools.exists():
        tools.write_text(
            "# User Preferences and Capabilities\n\n"
            "## Code Standards\n\n"
            "- Python 3.10+ (type hints, f-strings)\n"
            "- Prefer asyncio + OOP\n"
            "- Don't add needless comments — the code should be self-explanatory\n"
            "- Test against real data, don't use mocks\n\n"
            "## Expert Delegation\n\n"
            "For complex tasks, use the specialist agents:\n"
            "- `ask_coder` — Writing code, testing, debugging, refactoring\n"
            "- `ask_researcher` — Web research, gathering information\n"
            "- `ask_analyst` — Data analysis, calculations, reporting\n"
            "- `ask_planner` — Task planning, prioritization\n\n"
            "## Memory\n\n"
            "- Save important information with `manage_memory`.\n"
            "- Use categories: preferences, projects, decisions, learnings\n"
            "- Don't store sensitive data (API keys, passwords).\n\n"
            "## Context\n\n"
            "- Keep CONTEXT.md current with `update_context`.\n"
            "- Update project, decision, and status changes.\n",
            encoding="utf-8",
        )

    # Default CONTEXT.md
    context = workspace / "CONTEXT.md"
    if not context.exists():
        context.write_text(
            "# Current Context\n\n"
            "### Active Project\n"
            "No project set yet.\n\n"
            "### Recent Decisions\n"
            "No decisions recorded yet.\n\n"
            "### Notes\n"
            "No notes added yet.\n",
            encoding="utf-8",
        )

    # SOP directory
    sops_dir = workspace / "sops"
    sops_dir.mkdir(exist_ok=True)

    # Session directory
    sessions = Path(config.paths.sessions).expanduser()
    sessions.mkdir(parents=True, exist_ok=True)

    # Log directory
    logs = Path(config.paths.logs).expanduser()
    logs.mkdir(parents=True, exist_ok=True)

    # Memory DB directory
    if config.memory.enabled:
        memory_dir = Path(config.memory.db_path).expanduser().parent
        memory_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
