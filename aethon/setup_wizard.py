"""Interactive first-run setup wizard (`aethon init`).

Guides the user to a Strands provider — OpenAI (official API or an OpenAI-compatible
endpoint), Anthropic, or Ollama (fully local) — then validates the choice and writes
``~/.aethon/config.yaml``. The default is OpenAI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from aethon.agent.model_factory import check_model_availability
from aethon.config import AethonConfig, ModelConfig

console = Console()

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"

# provider -> (description, default_model, needs_api_key, api_key_env)
PROVIDERS: dict[str, tuple[str, str, bool, Optional[str]]] = {
    "openai": (
        "OpenAI API, or any OpenAI-compatible endpoint (set the host/base URL)",
        "gpt-4o",
        True,
        "OPENAI_API_KEY",
    ),
    "anthropic": (
        "Claude via an Anthropic API key (per-token billing)",
        "claude-opus-4-8",
        True,
        "ANTHROPIC_API_KEY",
    ),
    "ollama": (
        "Local models via Ollama — fully offline, no API key",
        "llama3.1",
        False,
        None,
    ),
}


def build_model_config(provider: str, *, model_id: str, api_key: str = "", host: str = "") -> dict:
    """Build the ``model:`` section of config.yaml (pure — no I/O)."""
    model: dict = {"provider": provider, "model_id": model_id}
    if provider == "ollama":
        model["host"] = host or _OLLAMA_DEFAULT_HOST
    elif host:
        # OpenAI-compatible base URL (e.g. a local proxy). Empty = official API.
        model["host"] = host
    if api_key:
        model["api_key"] = api_key
    return model


def build_memory_config(provider: str, enable: bool, api_key: str = "") -> dict:
    """Build the ``memory:`` section. Embeddings need Ollama or an OpenAI key."""
    if not enable:
        return {"enabled": False}
    if provider == "openai" and api_key:
        return {
            "enabled": True,
            "embedding_provider": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_api_key": api_key,
        }
    return {"enabled": True, "embedding_provider": "ollama", "embedding_model": "nomic-embed-text"}


def _wizard_channels() -> dict:
    """Optionally enable messaging bots and collect their tokens."""
    channels: dict = {}
    console.print("\n[bold]Messaging bots[/] (optional)")
    if click.confirm("  Enable Telegram?", default=False):
        token = click.prompt("    Telegram bot token (from @BotFather)", hide_input=True, default="").strip()
        channels["telegram"] = {"enabled": True, "token": token}
    if click.confirm("  Enable Discord?", default=False):
        token = click.prompt("    Discord bot token", hide_input=True, default="").strip()
        channels["discord"] = {"enabled": True, "token": token}
    if click.confirm("  Enable Slack?", default=False):
        bot_token = click.prompt("    Slack bot token (xoxb-...)", hide_input=True, default="").strip()
        app_token = click.prompt("    Slack app token (xapp-...)", hide_input=True, default="").strip()
        channels["slack"] = {"enabled": True, "bot_token": bot_token, "app_token": app_token}
    return channels


def _ensure_embedding_model(memory_cfg: dict) -> None:
    """If using Ollama embeddings, make sure the model is available — offer to install
    Ollama and/or pull the model. Optional and non-fatal."""
    import shutil
    import subprocess

    if not memory_cfg.get("enabled") or memory_cfg.get("embedding_provider") != "ollama":
        return
    model = memory_cfg.get("embedding_model", "nomic-embed-text")

    if shutil.which("ollama") is None:
        console.print(f"\n[yellow]Memory needs Ollama for embeddings, but it isn't installed.[/]")
        if shutil.which("brew") and click.confirm("  Install Ollama now with Homebrew?", default=False):
            try:
                subprocess.run(["brew", "install", "ollama"], check=True)
            except Exception as e:
                console.print(f"  [yellow]Install failed ({e}).[/]")
        else:
            console.print("  Install it from [bold]https://ollama.com/download[/], then re-run [bold]aethon init[/].")
            return
        if shutil.which("ollama") is None:
            return

    # Ollama is present — check the embedding model is pulled.
    try:
        listed = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        listed = ""
    if model.split(":")[0] in listed:
        console.print(f"[green]Embedding model '{model}' is ready.[/]")
        return
    if click.confirm(f"  Pull the embedding model '{model}' now (~270 MB)?", default=True):
        console.print(f"[dim]Running: ollama pull {model}[/]")
        try:
            subprocess.run(["ollama", "pull", model], check=True)
            console.print(f"[green]✓ Pulled {model}[/]")
        except Exception as e:
            console.print(f"[yellow]Pull failed ({e}). Run it yourself: ollama pull {model}[/]")


def run_wizard(config_path: str = "~/.aethon/config.yaml", *, force: bool = False) -> Optional[Path]:
    """Run the interactive setup. Returns the written path, or None if aborted."""
    path = Path(config_path).expanduser()

    console.print("\n[bold cyan]AETHON setup[/]\n")
    if path.exists() and not force:
        if not click.confirm(f"{path} already exists. Overwrite it?", default=False):
            console.print("[yellow]Keeping the existing config.[/]")
            return path

    console.print("Which AI provider should AETHON use?")
    keys = list(PROVIDERS)
    for i, key in enumerate(keys, 1):
        console.print(f"  [bold]{i}[/]. {key} — {PROVIDERS[key][0]}")
    idx = click.prompt("Provider", type=click.IntRange(1, len(keys)), default=1)
    provider = keys[idx - 1]
    _desc, default_model, needs_key, api_key_env = PROVIDERS[provider]

    model_id = click.prompt("Model id", default=default_model)

    host = ""
    if provider == "ollama":
        host = click.prompt("Ollama host", default=_OLLAMA_DEFAULT_HOST)
    elif provider == "openai":
        # Optional: a local OpenAI-compatible endpoint (e.g. a proxy). Blank = official API.
        host = click.prompt(
            "OpenAI base URL (leave blank for the official API; or a local endpoint)",
            default="",
        ).strip()

    api_key = ""
    if needs_key:
        env_val = os.getenv(api_key_env or "")
        if env_val:
            console.print(f"[dim]Found {api_key_env} in your environment — referencing it from config.[/]")
            api_key = "${" + (api_key_env or "") + "}"  # resolved at load time
        else:
            api_key = click.prompt(f"{provider} API key", hide_input=True, default="").strip()

    model = build_model_config(provider, model_id=model_id, api_key=api_key, host=host)

    # Validate the choice (network check for ollama; key presence for the API providers).
    available, msg = check_model_availability(ModelConfig(**model))
    console.print(f"\nProvider check: [{'green' if available else 'yellow'}]{msg}[/]")
    if not available and not click.confirm("Provider isn't ready yet. Save the config anyway?", default=True):
        console.print("[yellow]Aborted — re-run `aethon init` when the provider is ready.[/]")
        return None

    enable_memory = click.confirm(
        "Enable long-term memory? (needs Ollama or an OpenAI key for embeddings)",
        default=(provider in ("ollama", "openai")),
    )
    memory_cfg = build_memory_config(provider, enable_memory, api_key)
    _ensure_embedding_model(memory_cfg)

    channels_cfg = _wizard_channels()

    data: dict = {"model": model, "memory": memory_cfg}
    if channels_cfg:
        data["channels"] = channels_cfg
    written = AethonConfig.write(data, config_path)

    console.print(f"\n[green]✓ Wrote config to {written}[/]")
    if channels_cfg:
        console.print(f"  Enabled channels: {', '.join(channels_cfg)} + CLI/WebChat")
    console.print("Start AETHON with: [bold]aethon start[/]\n")
    return written
