"""AETHON configuration system.

YAML config loading with environment variable resolution and Pydantic validation.
"""

from pathlib import Path
from typing import Optional

import os
import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model provider configuration.

    Defaults to ``meridian`` — Claude on your Claude Max subscription quota via
    the local Meridian proxy (https://github.com/mertozbas/strands-meridian).
    Set ``provider: ollama`` (with ``host``/``model_id``) to run fully locally.
    """

    provider: str = "meridian"
    host: str = "http://localhost:11434"  # Ollama default; Meridian ignores it and uses 127.0.0.1:3456
    model_id: str = "claude-opus-4-8"     # most capable model; 1M context included with Claude Max
    api_key: str = ""
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40
    max_tokens: int = 8192
    region: str = "us-west-2"
    extra: dict = Field(default_factory=dict)


class WebChatChannelConfig(BaseModel):
    enabled: bool = True
    port: int = 18790
    # Bind address. Defaults to loopback (only reachable from this machine).
    # Set to "0.0.0.0" to expose on the network or inside a container (e.g. Docker
    # port mapping). When binding beyond loopback, also set dashboard.auth_token.
    host: str = "127.0.0.1"


class CLIChannelConfig(BaseModel):
    enabled: bool = True


class TelegramChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""


class DiscordChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""


class SlackChannelConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    app_token: str = ""


class WhatsAppChannelConfig(BaseModel):
    enabled: bool = False


class ChannelsConfig(BaseModel):
    cli: CLIChannelConfig = CLIChannelConfig()
    webchat: WebChatChannelConfig = WebChatChannelConfig()
    telegram: TelegramChannelConfig = TelegramChannelConfig()
    discord: DiscordChannelConfig = DiscordChannelConfig()
    slack: SlackChannelConfig = SlackChannelConfig()
    whatsapp: WhatsAppChannelConfig = WhatsAppChannelConfig()


class SecurityConfig(BaseModel):
    workspace_only: bool = True
    require_approval: list[str] = Field(
        default_factory=lambda: ["shell", "file_write", "send_message"]
    )
    blocked_commands: list[str] = Field(
        default_factory=lambda: ["rm -rf /", "sudo", "mkfs"]
    )
    allowed_senders: dict[str, list[str]] = Field(default_factory=dict)


class MemoryConfig(BaseModel):
    """Vector memory configuration."""

    enabled: bool = True
    embedding_provider: str = "ollama"  # ollama, openai
    embedding_model: str = "nomic-embed-text"
    embedding_api_key: str = ""
    db_path: str = "~/.aethon/memory.sqlite"


class MultiAgentConfig(BaseModel):
    """Multi-agent system configuration."""

    enabled: bool = True
    max_handoffs: int = 10
    max_iterations: int = 10
    execution_timeout: float = 300.0
    node_timeout: float = 120.0


class SOPConfig(BaseModel):
    """SOP execution configuration."""

    enabled: bool = True
    builtin_sops_enabled: bool = True


class ApprovalConfig(BaseModel):
    """Approval hook configuration (interrupt-based)."""

    enabled: bool = False
    requires_approval: list[str] = Field(
        default_factory=lambda: ["shell", "file_write"]
    )


class TelemetryConfig(BaseModel):
    """Telemetry hook configuration."""

    enabled: bool = True
    max_history: int = 10000


class MemoryGuardConfig(BaseModel):
    """Memory guard hook configuration."""

    enabled: bool = True
    custom_patterns: list[str] = Field(default_factory=list)


class SchedulerConfig(BaseModel):
    """APScheduler configuration."""

    enabled: bool = True
    default_channel: str = "cli"  # cli is enabled by default; telegram is opt-in
    jobs: dict = Field(default_factory=dict)


class DashboardConfig(BaseModel):
    """Web dashboard configuration."""

    enabled: bool = True
    pixel_agents: bool = True
    # Optional shared token. Empty = no auth (fine for the default localhost bind).
    # Set this before exposing the dashboard on a network — it then gates all
    # /api/* and /ws/dashboard access. Pass it via ?token=... (a cookie is set),
    # an `Authorization: Bearer` header, or the `aethon_dash` cookie.
    auth_token: str = ""


class WebhookConfig(BaseModel):
    """Webhook endpoint configuration."""

    enabled: bool = True
    secret: str = ""


class MCPConfig(BaseModel):
    """MCP server integration configuration."""

    enabled: bool = False
    servers: list[dict] = Field(default_factory=list)


class PerformanceConfig(BaseModel):
    """Performance optimization configuration."""

    # Off by default: warm-up sends a real model request on every boot, which would
    # spend Claude Max quota for no user benefit. Opt in if you want lower first-message latency.
    model_warmup: bool = False
    session_cache_size: int = 10
    embedding_cache_size: int = 100


class SessionConfig(BaseModel):
    storage_dir: str = "~/.aethon/sessions"
    conversation_manager: str = "summarizing"
    summary_ratio: float = 0.3
    preserve_recent_messages: int = 10


class PathsConfig(BaseModel):
    workspace: str = "~/.aethon/workspace"
    sessions: str = "~/.aethon/sessions"
    memory_db: str = "~/.aethon/memory.sqlite"
    logs: str = "~/.aethon/logs"
    credentials: str = "~/.aethon/credentials"


class MeridianConfig(BaseModel):
    """Meridian proxy lifecycle (used when provider is 'meridian')."""

    # Start Meridian automatically (in the background) on `aethon start` if it
    # isn't already running. Set false to manage Meridian yourself.
    auto_start: bool = True


class AethonConfig(BaseModel):
    """Root configuration model."""

    model: ModelConfig = ModelConfig()
    meridian: MeridianConfig = MeridianConfig()
    channels: ChannelsConfig = ChannelsConfig()
    security: SecurityConfig = SecurityConfig()
    session: SessionConfig = SessionConfig()
    memory: MemoryConfig = MemoryConfig()
    multi_agent: MultiAgentConfig = MultiAgentConfig()
    sops: SOPConfig = SOPConfig()
    approval: ApprovalConfig = ApprovalConfig()
    telemetry: TelemetryConfig = TelemetryConfig()
    memory_guard: MemoryGuardConfig = MemoryGuardConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    dashboard: DashboardConfig = DashboardConfig()
    webhook: WebhookConfig = WebhookConfig()
    mcp: MCPConfig = MCPConfig()
    performance: PerformanceConfig = PerformanceConfig()
    paths: PathsConfig = PathsConfig()

    @classmethod
    def load(cls, config_path: str = "~/.aethon/config.yaml") -> "AethonConfig":
        """Load config from YAML file."""
        path = Path(config_path).expanduser()
        if path.exists():
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            raw = cls._resolve_env_vars(raw)
            return cls(**raw)
        return cls()

    @staticmethod
    def _resolve_env_vars(data):
        """Resolve ${VAR_NAME} format environment variables."""
        if isinstance(data, str):
            if data.startswith("${") and data.endswith("}"):
                var_name = data[2:-1]
                return os.environ.get(var_name, "")
            return data
        elif isinstance(data, dict):
            return {k: AethonConfig._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AethonConfig._resolve_env_vars(item) for item in data]
        return data

    @staticmethod
    def write(data: dict, config_path: str = "~/.aethon/config.yaml") -> Path:
        """Write a config dict to a YAML file, creating parent dirs. Returns the path."""
        path = Path(config_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        return path
