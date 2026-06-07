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

    Defaults to ``openai``: set ``api_key`` for the official OpenAI API, or point
    ``host`` at a local OpenAI-compatible endpoint (base_url). Other providers:
    ``anthropic``, ``ollama`` (fully local), ``bedrock``, ``gemini``, ``litellm``,
    ``mistral``. Pick and configure one with ``aethon init``.
    """

    provider: str = "openai"
    host: str = "http://localhost:11434"  # Ollama default; openai treats this default as "unset" and uses the official API
    model_id: str = "gpt-4o"
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
    # Run tools without the interactive consent prompt that strands-tools shows for
    # shell/file_write/etc. AETHON runs headless (gateway/bots) where such a prompt
    # would hang, and it has its own guardrails (blocked_commands + the optional
    # approval hook), so this defaults to True. Set False to restore per-tool prompts.
    bypass_tool_consent: bool = True
    # When True, file tools are confined to ~/.aethon/workspace. Default False so the
    # assistant can work on your projects anywhere under $HOME (sensitive system and
    # credential paths are always blocked regardless of this flag).
    workspace_only: bool = False
    # NOTE: approval gating is provided by the separate `approval` section (disabled
    # by default). This list is reserved and is not currently wired to a hook.
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
    # Embedding endpoint for the `ollama` provider — independent of the chat model's
    # host (so memory keeps working when the model points at a non-Ollama endpoint).
    embedding_host: str = "http://localhost:11434"
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


class PromptConfig(BaseModel):
    """System-prompt composition options.

    Controls which optional awareness layers the SystemPromptComposer injects.
    Shell history is off by default for privacy; everything else is low-risk.
    """

    include_environment: bool = True
    include_shell_history: bool = False  # privacy — opt-in
    include_recent_logs: bool = True
    include_learnings: bool = True
    shell_history_lines: int = 50
    log_lines: int = 50
    session_id_format: str = "aethon-{date}"


class MacOSConfig(BaseModel):
    """macOS native integration (use_mac + apple_notes).

    Effective only on Darwin — registration is platform-guarded, so these flags
    are inert on other operating systems. The two most powerful action groups
    (Messages and Keychain) default OFF and must be explicitly opted into; the
    security hook hard-blocks their actions while disabled. ``apple_notes`` is
    registered only when ``enable_notes`` is set.
    """

    enabled: bool = True
    enable_calendar: bool = True
    enable_reminders: bool = True
    enable_mail: bool = True
    enable_notes: bool = True
    enable_shortcuts: bool = True
    enable_messages: bool = False  # explicit opt-in
    enable_keychain: bool = False  # explicit opt-in (security)
    # Actions gated by the approval hook (only when approval.enabled and use_mac
    # is on the requires_approval list). Identifiers are use_mac action names.
    actions_requiring_approval: list[str] = Field(
        default_factory=lambda: ["mail.send", "messages.send", "keychain.set"]
    )


class CapabilityFlag(BaseModel):
    """Simple on/off toggle for a vendored capability tool."""

    enabled: bool = True


class NotifyCapability(BaseModel):
    """Native notification capability."""

    enabled: bool = True
    method: str = "auto"  # auto | native | tui | bell | speak | sound | all


class CapabilitiesConfig(BaseModel):
    """Toggles for the vendored capability tools.

    Grouped on/off flags for low-risk utility tools (web scraping, GitHub GraphQL,
    JSON-RPC, native notifications). Each tool is import-guarded at registration, so
    a missing optional dependency simply skips it rather than breaking startup.
    """

    scraper: CapabilityFlag = CapabilityFlag()
    github: CapabilityFlag = CapabilityFlag()
    jsonrpc: CapabilityFlag = CapabilityFlag()
    notify: NotifyCapability = NotifyCapability()


class PerformanceConfig(BaseModel):
    """Performance optimization configuration."""

    # Off by default: warm-up sends a real model request on every boot, which would
    # spend API credits/quota for no user benefit. Opt in if you want lower first-message latency.
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


class AethonConfig(BaseModel):
    """Root configuration model."""

    model: ModelConfig = ModelConfig()
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
    macos: MacOSConfig = MacOSConfig()
    prompt: PromptConfig = PromptConfig()
    capabilities: CapabilitiesConfig = CapabilitiesConfig()
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
