"""AETHON CLI entry point."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

from aethon.config import AethonConfig
from aethon.gateway.server import AethonGateway

console = Console()


@click.group()
def main():
    """AETHON — Kisisel AI Asistan"""
    pass


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config dosya yolu")
def start(config: str):
    """AETHON'u baslat."""
    console.print("[bold cyan]AETHON[/] baslatiliyor...\n")

    cfg = AethonConfig.load(config)

    _ensure_workspace(cfg)

    from aethon.agent.model_factory import check_model_availability

    available, msg = check_model_availability(cfg.model)
    if not available:
        console.print(f"[red]HATA:[/] {msg}")
        return

    console.print(f"  Provider: [green]{cfg.model.provider}[/]")
    console.print(f"  Model: [green]{cfg.model.model_id}[/]")
    console.print(f"  WebChat: [green]http://127.0.0.1:{cfg.channels.webchat.port}[/]")

    # Embedding model kontrolu (VectorMemory icin)
    if cfg.memory.enabled:
        _check_embedding_model(cfg)

    # Multi-agent durumu
    if cfg.multi_agent.enabled:
        console.print("  Multi-Agent: [green]aktif[/]")
    else:
        console.print("  Multi-Agent: [dim]devre disi[/]")

    # SOP durumu
    if cfg.sops.enabled:
        try:
            from aethon.sops.runner import SOPRunner

            sop_dirs = [str(Path(cfg.paths.workspace).expanduser() / "sops")]
            runner = SOPRunner(sop_dirs, cfg.sops.builtin_sops_enabled)
            sop_count = len(runner.list_sops())
            console.print(f"  SOP'lar: [green]{sop_count} adet[/]")
        except Exception:
            console.print("  SOP'lar: [yellow]yuklenemedi[/]")

    # Scheduler durumu
    if cfg.scheduler.enabled:
        console.print("  Zamanlayici: [green]aktif[/]")
    else:
        console.print("  Zamanlayici: [dim]devre disi[/]")

    # Telemetry durumu
    if cfg.telemetry.enabled:
        console.print("  Telemetri: [green]aktif[/]")
    else:
        console.print("  Telemetri: [dim]devre disi[/]")

    # Dashboard durumu
    if cfg.dashboard.enabled and cfg.channels.webchat.enabled:
        console.print(
            f"  Dashboard: [green]http://127.0.0.1:{cfg.channels.webchat.port}/dashboard[/]"
        )

    # Webhook durumu
    if cfg.webhook.enabled and cfg.channels.webchat.enabled:
        console.print(
            f"  Webhook: [green]http://127.0.0.1:{cfg.channels.webchat.port}/webhook/{{channel}}[/]"
        )

    # MCP durumu
    if cfg.mcp.enabled:
        console.print(f"  MCP: [green]{len(cfg.mcp.servers)} sunucu[/]")
    else:
        console.print("  MCP: [dim]devre disi[/]")

    # Etkin kanallari listele
    _print_channels(cfg)

    console.print()

    gateway = AethonGateway(cfg)
    try:
        asyncio.run(gateway.start())
    except KeyboardInterrupt:
        pass  # Signal handler already triggered graceful shutdown


def _check_embedding_model(config: AethonConfig):
    """Check if embedding model is available in Ollama."""
    import requests

    try:
        r = requests.get(f"{config.model.host}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        emb_model = config.memory.embedding_model
        if any(emb_model in m for m in models):
            console.print(f"  Memory: [green]{emb_model}[/] (aktif)")
        else:
            console.print(
                f"  Memory: [yellow]{emb_model} bulunamadi[/] — "
                f"ollama pull {emb_model}"
            )
    except Exception:
        console.print("  Memory: [yellow]Ollama erisim hatasi[/]")


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
    console.print(f"  Kanallar: [green]{', '.join(channels)}[/]")


def _ensure_workspace(config: AethonConfig):
    """Create workspace directory with default files if not exists."""
    workspace = Path(config.paths.workspace).expanduser()
    workspace.mkdir(parents=True, exist_ok=True)

    # Default SOUL.md
    soul = workspace / "SOUL.md"
    if not soul.exists():
        soul.write_text(
            "# AETHON — Kisilik\n\n"
            "Sen AETHON, Mert'in kisisel AI asistanisin.\n"
            "Mac uzerinde Ollama ile calisiyorsun.\n\n"
            "## Davranis\n"
            "- Turkce ve Ingilizce konusabilirsin.\n"
            "- Kisa ve oz yanit ver.\n"
            "- Hata yaptiginda kabul et ve duzelt.\n",
            encoding="utf-8",
        )

    # Default TOOLS.md
    tools = workspace / "TOOLS.md"
    if not tools.exists():
        tools.write_text(
            "# Kullanici Tercihleri\n\n"
            "- Python 3.10+ kullan\n"
            "- asyncio + OOP tercih et\n"
            "- Kodda yorum ekleme — kod kendini aciklamali\n",
            encoding="utf-8",
        )

    # Default CONTEXT.md
    context = workspace / "CONTEXT.md"
    if not context.exists():
        context.write_text(
            "# Mevcut Baglam\n\n"
            "Henuz bir baglam belirlenmedi.\n",
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
