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
    from aethon.setup_wizard import meridian_status

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

    up, status = meridian_status()
    console.print(f"  Meridian: [{'green' if up else 'yellow'}]{status}[/]")

    console.print(
        f"  Memory:   [{'green' if cfg.memory.enabled else 'dim'}]"
        f"{'enabled' if cfg.memory.enabled else 'disabled'}[/]"
        f" ({cfg.memory.embedding_provider} embeddings)"
    )
    console.print()


@main.command()
@click.option("--config", "-c", default="~/.aethon/config.yaml", help="Config dosya yolu")
def start(config: str):
    """AETHON'u baslat."""
    if not Path(config).expanduser().exists():
        console.print("[yellow]No config found — let's set up AETHON first.[/]")
        from aethon.setup_wizard import run_wizard

        if run_wizard(config) is None:
            return

    console.print("[bold cyan]AETHON[/] baslatiliyor...\n")

    cfg = AethonConfig.load(config)

    # Auto-start Meridian in the background if it's our provider and not already up,
    # so the user never has to launch it by hand or keep a terminal open.
    if cfg.model.provider == "meridian" and cfg.meridian.auto_start:
        from aethon.agent.model_factory import _meridian_base_url
        from aethon.meridian_manager import ensure_running, is_running

        base = _meridian_base_url(cfg.model) or "http://127.0.0.1:3456"
        if not is_running(base):
            console.print("  Meridian: [dim]starting in the background…[/]")
        ok, mmsg = ensure_running(base)
        console.print(f"  Meridian: [{'green' if ok else 'yellow'}]{mmsg}[/]")

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
    """Check if embedding model is available."""
    import requests

    emb_provider = getattr(config.memory, "embedding_provider", "ollama")
    emb_model = config.memory.embedding_model

    if emb_provider == "openai":
        emb_key = getattr(config.memory, "embedding_api_key", "")
        if emb_key:
            console.print(f"  Memory: [green]{emb_model}[/] (openai, aktif)")
        else:
            console.print(f"  Memory: [yellow]{emb_model}[/] (openai, API key eksik)")
        return

    # Default: Ollama
    try:
        r = requests.get(f"{config.model.host}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(emb_model in m for m in models):
            console.print(f"  Memory: [green]{emb_model}[/] (ollama, aktif)")
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
            "# AETHON — Ruh\n\n"
            "Sen AETHON, kisisel AI asistansin. Amacin kullanicinin hayatini "
            "kolaylastirmak, islerini hizlandirmak ve teknik konularda gercek "
            "bir partner olmak.\n\n"
            "## Kimlik\n\n"
            "- Pragmatik ve dogrudan ol.\n"
            "- Hatani kabul et, bahanenin arkasina saklanma.\n"
            "- Bilmedigini soyle — uydurma.\n\n"
            "## Iletisim\n\n"
            "- Turkce ve Ingilizce konusabilirsin. Kullanici hangi dilde "
            "yazarsa o dilde yanit ver.\n"
            "- Kisa, oz, net yanit ver. Gereksiz giris cumleleri yazma.\n"
            "- Yanitlarini Markdown formatinda ver. Baslik, kalin, kod blogu, "
            "liste kullan.\n\n"
            "## Karar Verme\n\n"
            "- Basit isler icin direkt yap, soru sorma.\n"
            "- Karmasik isler icin once plan sun.\n"
            "- Birden fazla yol varsa en basitini sec.\n",
            encoding="utf-8",
        )

    # Default TOOLS.md
    tools = workspace / "TOOLS.md"
    if not tools.exists():
        tools.write_text(
            "# Kullanici Tercihleri ve Yetenekler\n\n"
            "## Kod Standartlari\n\n"
            "- Python 3.10+ (type hint, f-string)\n"
            "- asyncio + OOP tercih et\n"
            "- Kodda gereksiz yorum ekleme — kod kendini aciklamali\n"
            "- Gercek veri ile test et, mock kullanma\n\n"
            "## Uzman Delegasyonu\n\n"
            "Karmasik gorevlerde uzman agentlari kullan:\n"
            "- `ask_coder` — Kod yazma, test, debug, refactor\n"
            "- `ask_researcher` — Web arastirma, bilgi toplama\n"
            "- `ask_analyst` — Veri analizi, hesaplama, rapor\n"
            "- `ask_planner` — Gorev planlama, onceliklendirme\n\n"
            "## Hafiza\n\n"
            "- Onemli bilgileri `manage_memory` ile kaydet.\n"
            "- Kategori kullan: preferences, projects, decisions, learnings\n"
            "- Hassas veri kaydetme (API key, sifre).\n\n"
            "## Baglam\n\n"
            "- `update_context` ile CONTEXT.md'yi canli tut.\n"
            "- Proje, karar ve durum degisikliklerini guncelle.\n",
            encoding="utf-8",
        )

    # Default CONTEXT.md
    context = workspace / "CONTEXT.md"
    if not context.exists():
        context.write_text(
            "# Mevcut Baglam\n\n"
            "### Aktif Proje\n"
            "Henuz bir proje belirlenmedi.\n\n"
            "### Son Kararlar\n"
            "Henuz karar kaydedilmedi.\n\n"
            "### Notlar\n"
            "Henuz not eklenmedi.\n",
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
