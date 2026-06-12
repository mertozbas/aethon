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

    # Diagnosing a BROKEN config is doctor's job — don't crash on malformed YAML.
    try:
        cfg = AethonConfig.load(config)
    except Exception as e:
        console.print(f"  [red]Config failed to load:[/] {type(e).__name__}: {e}")
        console.print(
            "  Fix the YAML (or re-run [bold]aethon init[/]). "
            "Still checking file permissions below.\n"
        )
        _report_path_permissions(cfg_path)
        console.print()
        return

    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model:    [green]{cfg.model.model_id}[/]")

    available, msg = check_model_availability(cfg.model)
    console.print(f"  Provider check: [{'green' if available else 'red'}]{msg}[/]")

    console.print(
        f"  Memory:   [{'green' if cfg.memory.enabled else 'dim'}]"
        f"{'enabled' if cfg.memory.enabled else 'disabled'}[/]"
        f" ({cfg.memory.embedding_provider} embeddings)"
    )

    _report_secrets_hygiene(cfg, cfg_path)
    _report_unknown_keys(cfg_path)
    console.print()


def _report_unknown_keys(cfg_path: Path) -> None:
    """Flag config keys the schema doesn't recognize (typos, removed keys) — H8."""
    import yaml

    from aethon.config import unknown_config_keys

    try:
        with open(cfg_path) as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return
    unknown = unknown_config_keys(raw)
    if unknown:
        console.print(
            "  [yellow]Unknown config keys[/] (typo or removed?): "
            + ", ".join(unknown)
        )


def _report_path_permissions(cfg_path: Path, credentials: Path | None = None) -> None:
    """Flag world-/group-readable config / home / credential paths (S8)."""
    import stat

    def _check(label: str, p: Path) -> None:
        if not p.exists():
            return
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o077:
            console.print(
                f"  [red]{label} is group/world-readable[/] "
                f"(0{mode:03o}) — chmod {'700' if p.is_dir() else '600'} {p}"
            )
        else:
            console.print(f"  {label}: [green]0{mode:03o}[/]")

    console.print("  [bold]Secrets hygiene:[/]")
    _check("config.yaml", cfg_path)
    _check("~/.aethon", cfg_path.parent)
    if credentials is not None:
        _check("credentials/", credentials)


def _report_secrets_hygiene(cfg: AethonConfig, cfg_path: Path) -> None:
    """Permission report + a nudge away from a literally-stored API key (S8)."""
    _report_path_permissions(cfg_path, Path(cfg.paths.credentials).expanduser())

    # Check the RAW file (loaded cfg already resolved ${ENV_VAR} to its value).
    import yaml

    try:
        with open(cfg_path) as f:
            raw = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        raw = {}
    raw_key = ((raw.get("model") or {}).get("api_key") or "")
    if raw_key and not (raw_key.startswith("${") and raw_key.endswith("}")):
        console.print(
            "  [yellow]model.api_key is stored literally[/] — prefer a "
            "${ENV_VAR} reference (see `aethon init`)."
        )


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config file path")
def mcp(config: str):
    """Serve AETHON's tools to MCP clients (e.g. Claude Desktop) over stdio."""
    # stdio is the MCP transport — keep all informational output on stderr so it
    # never corrupts the JSON-RPC protocol stream on stdout.
    if not Path(config).expanduser().exists():
        click.echo("No config found. Run 'aethon init' first.", err=True)
        return
    try:
        from aethon.tools.mcp_server import run_mcp_server
    except ImportError:
        click.echo(
            "MCP support requires the 'mcp' extra: pip install aethon-ai[mcp]",
            err=True,
        )
        return
    click.echo("AETHON MCP server starting (stdio)…", err=True)
    run_mcp_server(config)


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config file path")
@click.option(
    "--insecure-bind",
    is_flag=True,
    help="Allow a non-loopback bind without dashboard.auth_token "
    "(only behind your own authenticating reverse proxy).",
)
def start(config: str, insecure_bind: bool):
    """Start AETHON."""
    if not Path(config).expanduser().exists():
        console.print("[yellow]No config found — let's set up AETHON first.[/]")
        from aethon.setup_wizard import run_wizard

        if run_wizard(config) is None:
            return

    console.print("[bold cyan]AETHON[/] starting...\n")

    # Quiet benign, repetitive provider warnings out of the chat (e.g. reasoning models
    # like gpt-5.x emit reasoningContent that the Chat Completions API can't carry across
    # turns — Strands logs it every turn). Real errors still surface.
    import logging as _logging
    _logging.getLogger("strands.models.openai").setLevel(_logging.ERROR)
    # Proxies/reasoning models often report stop_reason=end_turn even when the
    # response carries toolUse blocks; Strands self-corrects to tool_use and logs
    # a warning every such turn. Benign and noisy — quiet it.
    _logging.getLogger("strands.event_loop.streaming").setLevel(_logging.ERROR)

    cfg = AethonConfig.load(config)

    # Fail closed before anything else: an exposed bind without auth is refused
    # at boot, not discovered at attack time (Phase 9A / S4).
    from aethon.gateway.netsec import (
        allowlist_gaps, check_bind_security, check_sandbox,
    )

    bind_ok, bind_msg = check_bind_security(cfg)
    if not bind_ok and not insecure_bind:
        console.print(f"[red]Refusing to start:[/] {bind_msg}")
        return

    sandbox_ok, sandbox_msg = check_sandbox(cfg)
    if not sandbox_ok:
        console.print(f"[red]Refusing to start:[/] {sandbox_msg}")
        return

    # Default-deny senders (S5): warn up front when a bot would reject everyone.
    for channel in allowlist_gaps(cfg):
        console.print(
            f"[yellow]Warning:[/] {channel} has no "
            f"security.allowed_senders.{channel} — every sender will be rejected."
        )

    _ensure_workspace(cfg)
    _setup_file_logging(cfg)

    from aethon.agent.model_factory import check_model_availability

    available, msg = check_model_availability(cfg.model)
    if not available:
        console.print(f"[red]Provider not ready:[/] {msg}")
        console.print("Run [bold]aethon init[/] to reconfigure, or [bold]aethon doctor[/] to diagnose.")
        return

    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model: [green]{cfg.model.model_id}[/]")
    console.print(
        f"  WebChat: [green]http://{cfg.channels.webchat.host}:{cfg.channels.webchat.port}[/]"
    )

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
            f"  Dashboard: [green]http://{cfg.channels.webchat.host}:"
            f"{cfg.channels.webchat.port}/dashboard[/]"
        )

    # Webhook status
    if cfg.webhook.enabled and cfg.channels.webchat.enabled:
        console.print(
            f"  Webhook: [green]http://{cfg.channels.webchat.host}:"
            f"{cfg.channels.webchat.port}/webhook/{{channel}}[/]"
        )

    # MCP status
    if cfg.mcp.enabled:
        console.print(f"  MCP: [green]{len(cfg.mcp.servers)} servers[/]")
    else:
        console.print("  MCP: [dim]disabled[/]")

    # List enabled channels
    _print_channels(cfg)

    console.print()

    # Single-instance guard (H6): two gateways on one ~/.aethon corrupt each
    # other (double writes, Telegram getUpdates conflict).
    from aethon.gateway.single_instance import SingleInstanceLock

    instance_lock = SingleInstanceLock(Path("~/.aethon/aethon.pid"))
    acquired, other_pid = instance_lock.acquire()
    if not acquired:
        console.print(
            f"[red]AETHON is already running[/] (pid {other_pid}). "
            "Stop the other instance first."
        )
        return

    gateway = AethonGateway(cfg, insecure_bind=insecure_bind)
    try:
        asyncio.run(gateway.start())
    except KeyboardInterrupt:
        pass  # Signal handler already triggered graceful shutdown
    finally:
        instance_lock.release()


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


def _setup_file_logging(config: AethonConfig) -> None:
    """Attach a rotating file handler to the ROOT logger (H9).

    Persists logs to <paths.logs>/aethon.log so the system prompt's recent-logs
    layer and post-hoc debugging have a source. Attached to root so third-party
    errors (strands, uvicorn, aiogram, discord, slack) reach the file too — not
    only ``aethon.*``. AETHON logs at ``logging.level``; libraries log at
    ``logging.third_party_level`` to keep the file readable. Console is
    unaffected.
    """
    import logging
    from logging.handlers import RotatingFileHandler

    log_cfg = getattr(config, "logging", None)
    if log_cfg is not None and not getattr(log_cfg, "enabled", True):
        return

    def _level(name: str, default: int) -> int:
        return getattr(logging, str(name).upper(), default)

    aethon_level = _level(getattr(log_cfg, "level", "INFO"), logging.INFO)
    third_party = _level(getattr(log_cfg, "third_party_level", "WARNING"), logging.WARNING)

    try:
        logs_dir = Path(config.paths.logs).expanduser()
        logs_dir.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger()  # ROOT — every logger propagates here
        for h in root.handlers:
            if getattr(h, "_aethon_file", False):
                return  # already configured
        handler = RotatingFileHandler(
            logs_dir / "aethon.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        handler._aethon_file = True
        handler.setLevel(logging.NOTSET)  # emit whatever the loggers pass through
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
        # Third-party floor at root; AETHON's own loggers at their configured level.
        root.setLevel(third_party)
        logging.getLogger("aethon").setLevel(aethon_level)
    except Exception:
        pass


def _secure_aethon_home() -> None:
    """Restrict ~/.aethon to the owner (S8) — it holds sessions, logs, and the
    config (which may carry plaintext keys). Best-effort; chmod no-ops where
    unsupported."""
    import os

    home = Path("~/.aethon").expanduser()
    try:
        if home.exists():
            os.chmod(home, 0o700)
    except OSError:
        pass


def _ensure_workspace(config: AethonConfig):
    """Create workspace directory with default files if not exists."""
    workspace = Path(config.paths.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)
    _secure_aethon_home()

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
            "## Persistent Learning\n\n"
            "- When you discover an important pattern, fix, or preference, record "
            "it with `record_learning(category='...', content='...')` so it "
            "persists across sessions (read back into your prompt from LEARNINGS.md).\n\n"
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
