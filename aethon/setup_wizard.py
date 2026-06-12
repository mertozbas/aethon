"""Interactive first-run setup wizard (`aethon init`).

Guides the user to a Strands provider — OpenAI (official API or an OpenAI-compatible
endpoint), Anthropic, or Ollama (fully local) — then validates the choice and writes
``~/.aethon/config.yaml``. The default is OpenAI.
"""

from __future__ import annotations

import os
import sys
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


def _telegram_chat_id(token: str) -> str:
    """Resolve the proactive chat id: auto-detect via getUpdates, else ask manually.

    Auto-detect is attempted only on an interactive TTY (so headless `aethon init`
    and CI/tests never make the live api.telegram.org call or block on the pause).
    """
    if token and sys.stdin.isatty():
        if click.confirm("    Auto-detect your chat id? (you'll message your bot)", default=True):
            console.print("    Open Telegram, send your bot any message, then come back.")
            click.prompt("    Press Enter once you've sent it", default="", show_default=False)
            try:
                import requests

                resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
                updates = (resp.json() or {}).get("result", [])
                for upd in reversed(updates):
                    chat = (upd.get("message") or upd.get("edited_message") or {}).get("chat") or {}
                    if chat.get("id") is not None:
                        cid = str(chat["id"])
                        console.print(f"    [green]Detected chat id: {cid}[/]")
                        return cid
                console.print("    [yellow]No recent message found — enter it manually.[/]")
            except Exception as e:
                console.print(f"    [yellow]Auto-detect failed ({e}) — enter it manually.[/]")
    return click.prompt(
        "    Telegram chat id (your numeric id; ask @userinfobot if unsure)", default=""
    ).strip()


def _wizard_channels() -> tuple[dict, dict]:
    """Optionally enable messaging bots and collect their tokens.

    Returns ``(channels, allowed_senders)`` — the latter restricts who may message
    a bot that has shell/tool access.
    """
    channels: dict = {}
    allowed: dict = {}
    console.print("\n[bold]Messaging bots[/] (optional)")
    if click.confirm("  Enable Telegram?", default=False):
        token = click.prompt("    Telegram bot token (from @BotFather)", hide_input=True, default="").strip()
        chat_id = _telegram_chat_id(token)
        channels["telegram"] = {"enabled": True, "token": token}
        if chat_id:
            channels["telegram"]["chat_id"] = chat_id
            if click.confirm(
                "    Restrict the bot to only respond to this chat id? "
                "(recommended — it has shell/tool access)",
                default=True,
            ):
                allowed.setdefault("telegram", []).append(chat_id)
    if click.confirm("  Enable Discord?", default=False):
        token = click.prompt("    Discord bot token", hide_input=True, default="").strip()
        channels["discord"] = {"enabled": True, "token": token}
        channel_id = click.prompt(
            "    Default destination for proactive sends "
            "(a channel id or your user id; empty = skip)",
            default="",
        ).strip()
        if channel_id:
            channels["discord"]["channel_id"] = channel_id
            if click.confirm(
                "    Restrict the bot to only respond to this id? "
                "(recommended — it has shell/tool access)",
                default=True,
            ):
                allowed.setdefault("discord", []).append(channel_id)
    if click.confirm("  Enable Slack?", default=False):
        bot_token = click.prompt("    Slack bot token (xoxb-...)", hide_input=True, default="").strip()
        app_token = click.prompt("    Slack app token (xapp-...)", hide_input=True, default="").strip()
        channels["slack"] = {"enabled": True, "bot_token": bot_token, "app_token": app_token}
        slack_dest = click.prompt(
            "    Default destination for proactive sends "
            "(channel id C... or your user id U...; empty = skip)",
            default="",
        ).strip()
        if slack_dest:
            channels["slack"]["channel"] = slack_dest
            if click.confirm(
                "    Restrict the bot to only respond to this id? "
                "(recommended — it has shell/tool access)",
                default=True,
            ):
                allowed.setdefault("slack", []).append(slack_dest)
    if click.confirm(
        "  Enable WhatsApp? (experimental — pairs via QR code at first start)",
        default=False,
    ):
        channels["whatsapp"] = {"enabled": True}
        chat = click.prompt(
            "    Your WhatsApp number for proactive sends "
            "(digits only, e.g. 905551112233; empty = skip)",
            default="",
        ).strip()
        if chat:
            channels["whatsapp"]["chat"] = chat
            if click.confirm(
                "    Restrict the bot to only respond to this number? "
                "(recommended — it has shell/tool access)",
                default=True,
            ):
                allowed.setdefault("whatsapp", []).append(chat)
    return channels, allowed


def _wizard_webhooks() -> dict:
    """Offer to protect the /webhook/* endpoints with an HMAC secret.

    Webhooks are enabled by default; without a secret they fail closed on any
    non-loopback bind (Phase 9A / S3), so a secret is the path to keeping them
    usable when AETHON is exposed.
    """
    console.print("\n[bold]Webhooks[/] (optional)")
    if not click.confirm(
        "  Protect webhook endpoints with a secret? "
        "(recommended — required when exposing beyond localhost)",
        default=True,
    ):
        return {}
    import secrets

    secret = secrets.token_hex(16)
    console.print(
        f"    Webhook secret: [bold]{secret}[/]\n"
        "    Callers must sign the request body with HMAC-SHA256 using this "
        "secret (header: X-Aethon-Signature)."
    )
    return {"secret": secret}


def _ensure_embedding_model(memory_cfg: dict) -> None:
    """If using Ollama embeddings, make sure the model is available — offer to install
    Ollama and/or pull the model. Optional and non-fatal."""
    import shutil
    import subprocess

    if not memory_cfg.get("enabled") or memory_cfg.get("embedding_provider") != "ollama":
        return
    model = memory_cfg.get("embedding_model", "nomic-embed-text")

    if shutil.which("ollama") is None:
        console.print("\n[yellow]Memory needs Ollama for embeddings, but it isn't installed.[/]")
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


def _backup_existing_config(path: Path) -> Optional[Path]:
    """Copy an existing config to a timestamped .bak before overwrite (H8)."""
    if not path.exists():
        return None
    import shutil
    from datetime import datetime

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    try:
        shutil.copy2(path, backup)
        return backup
    except OSError:
        return None


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
            # Secrets hygiene (S8): a literal key lands in the 0600 config, but an
            # env reference keeps it out of the file entirely. Nudge, don't force.
            if api_key and not api_key.startswith("${") and api_key_env:
                console.print(
                    f"[yellow]Note:[/] the key is stored in the config file (0600). "
                    f"To keep it out of the file, set [bold]{api_key_env}[/] in your "
                    f"environment and re-run — AETHON will reference it as "
                    f"[bold]${{{api_key_env}}}[/] instead."
                )

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

    channels_cfg, allowed_senders = _wizard_channels()
    webhook_cfg = _wizard_webhooks()

    data: dict = {"config_version": 1, "model": model, "memory": memory_cfg}
    if channels_cfg:
        data["channels"] = channels_cfg
    if allowed_senders:
        data["security"] = {"allowed_senders": allowed_senders}
    if webhook_cfg:
        data["webhook"] = webhook_cfg

    # Back up an existing config before overwriting it (H8) — never silently
    # destroy hand-edited settings.
    backup = _backup_existing_config(path)
    if backup:
        console.print(f"[dim]Backed up your previous config to {backup}[/]")

    written = AethonConfig.write(data, config_path)

    console.print(f"\n[green]✓ Wrote config to {written}[/]")
    if channels_cfg:
        console.print(f"  Enabled channels: {', '.join(channels_cfg)} + CLI/WebChat")
    console.print("Start AETHON with: [bold]aethon start[/]\n")
    return written
