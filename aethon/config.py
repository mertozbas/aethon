"""AETHON configuration system.

YAML config loading with environment variable resolution and Pydantic validation.
"""

from pathlib import Path

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
    # Extra browser Origins accepted on the WebSocket upgrades (/ws/chat and
    # /ws/dashboard) — full origins, e.g. "https://chat.example.com". Empty =
    # same-host origins only. Clients without an Origin header (curl, Python)
    # always pass; the token is their gate.
    allowed_origins: list[str] = Field(default_factory=list)


class CLIChannelConfig(BaseModel):
    enabled: bool = True


class TelegramChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""
    # Default destination for PROACTIVE/outbound sends (scheduler, send_message,
    # notifications). For a private 1:1 chat this equals your Telegram user id.
    # Reactive replies always answer the inbound chat and ignore this.
    chat_id: str = ""


class DiscordChannelConfig(BaseModel):
    enabled: bool = False
    token: str = ""
    # Default destination for PROACTIVE/outbound sends (scheduler, send_message,
    # notifications) — a channel id or a user id (DM). Reactive replies always
    # answer the inbound channel and ignore this.
    channel_id: str = ""


class SlackChannelConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    app_token: str = ""
    # Default destination for PROACTIVE/outbound sends — a channel id (C...),
    # user id (U..., opens the app DM) or channel name. Reactive replies always
    # answer the inbound channel and ignore this.
    channel: str = ""


class WhatsAppChannelConfig(BaseModel):
    enabled: bool = False
    # Default destination for PROACTIVE/outbound sends — a phone number / chat
    # user id. Reactive replies always answer the inbound chat and ignore this.
    chat: str = ""


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
    # Wrap results from external-content tools (scraper, http_request, jsonrpc,
    # use_github) and webhook payloads in [UNTRUSTED EXTERNAL CONTENT] markers so
    # the model treats them as data, not instructions (Phase 9A / S9). This is
    # honest marking, NOT an injection detector. On by default (cheap, advisory).
    mark_untrusted_content: bool = True
    # Execution sandbox for the `shell` tool (Phase 9A / S7).
    #   "none"   — shell runs on the host under the blocklist (current default).
    #   "docker" — shell runs in a per-session container (workspace mounted, no
    #              host home, no host network by default, resource caps). The
    #              real boundary: bypassing the blocklist no longer matters when
    #              the blast radius is a disposable container. File tools stay
    #              host-side in this version (documented). Refuses to start if
    #              docker is selected but unavailable (fail closed).
    sandbox: str = "none"
    sandbox_image: str = "python:3.12-slim"
    sandbox_network: str = "none"  # docker --network; "none" = no host/network access
    sandbox_memory: str = "512m"   # docker --memory cap
    sandbox_cpus: str = "1.0"      # docker --cpus cap
    sandbox_pids_limit: int = 256  # docker --pids-limit cap
    sandbox_timeout: int = 60      # seconds per shell command


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
        default_factory=lambda: ["shell", "file_write", "manage_tools"]
    )
    # Seconds to wait for a human approval answer before denying (S6). Generous
    # by default — the prompt is local (CLI/WebChat) or push (Telegram).
    timeout_seconds: float = 120.0


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


class RuntimeToolsConfig(BaseModel):
    """Dynamic tool loading (``manage_tools``).

    Off by default — opt-in. ``enabled`` gates registration; ``allow_create``
    permits create/fetch (the subprocess sandbox validates first); ``allow_install``
    permits add/reload (auto-installing missing packages). The SecurityHookProvider
    enforces these per action.
    """

    enabled: bool = False
    allow_create: bool = False
    allow_install: bool = False
    sandbox_timeout: int = 30
    cache_dir: str = "~/.aethon/runtime_tools_cache"


class AmbientConfig(BaseModel):
    """Ambient / autonomous mode.

    Opt-in and runtime-toggleable. Defaults keep it fully dormant: with
    ``enabled=False`` no ambient tools are registered and no background task ever
    runs. ``start_ambient_mode`` / ``stop_ambient_mode`` are the runtime switch.
    """

    enabled: bool = False
    auto_start: bool = False
    idle_threshold_seconds: int = 30
    max_iterations: int = 15
    cooldown_seconds: int = 60
    autonomous_cooldown_seconds: int = 10
    autonomous_max_iterations: int = 100
    completion_signal: str = "[AMBIENT_DONE]"


class SessionRecorderConfig(BaseModel):
    """Session recording (timeline + snapshots, exported to a ZIP for replay).

    Off by default. Recordings are written to ``paths.recordings`` on shutdown.
    """

    enabled: bool = False
    max_events: int = 10000
    # OS-level monkeypatching of open/requests — left off; AETHON records via the
    # hook provider instead.
    install_hooks: bool = False
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            "KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH"
        ]
    )
    max_sessions_kept: int = 20


class LSPConfig(BaseModel):
    """Language Server Protocol integration.

    Off by default to avoid spawning language servers on boot. Install servers
    separately: pyright via the ``[lsp]`` extra; typescript-language-server /
    gopls / rust-analyzer / clangd on PATH for those languages.
    """

    enabled: bool = False
    auto_diagnostics: bool = False  # append diagnostics after file-modifying tools


class ReliabilityConfig(BaseModel):
    """Reliability hardening (Phase 8) — the verification backstop.

    All gates are ADVISORY by default (they append feedback, mirroring the
    LSP diagnostics pattern) so they add no friction; ``strict`` flips them
    to hard gates. See docs/development/PHASE-8-RELIABILITY.md.
    """

    # Escalate findings from advisory feedback to hard gates (failed verify
    # marks the tool result as error; completion gate re-prompts the agent).
    strict: bool = False
    # PostEditVerify hook — run a verify command on files the agent edits and
    # append a [Verify] PASS/FAIL block to the tool result.
    post_edit_verify: bool = True
    # Verify command. ``{paths}`` is replaced with the edited file paths; a
    # command without the placeholder runs as-is (e.g. "pytest -q").
    # Empty = auto-detect: ``ruff check`` on edited *.py files when ruff is
    # on PATH, otherwise skip silently.
    verify_cmd: str = ""
    # Seconds before a verify run is abandoned (logged, never blocks forever).
    verify_timeout: int = 30
    # CompletionGate hook — when a reply asserts success but no verification
    # evidence exists for the files edited, append a Definition-of-Done
    # reminder instead of returning the claim clean.
    completion_gate: bool = True
    # AnglicizationGuard hook — pause edits that replace existing Turkish
    # text with English-only text (advisory: an identical re-issue passes).
    anglicization_guard: bool = True
    # InputValidator hook — cancel malformed tool calls (empty shell command,
    # missing file path) with a self-describing reason.
    input_validator: bool = True


class PromptConfig(BaseModel):
    """System-prompt composition options.

    Controls which optional awareness layers the SystemPromptComposer injects.
    Shell history is off by default for privacy; everything else is low-risk.
    """

    include_environment: bool = True
    include_shell_history: bool = False  # privacy — opt-in
    include_recent_logs: bool = True
    include_learnings: bool = True
    include_self_awareness: bool = False  # embed key source files — opt-in
    include_tasks: bool = True  # task-ledger snapshot (## Open Tasks)
    include_handoff: bool = True  # reset checkpoints (## Handoff)
    include_operating_rules: bool = True  # policy-as-code layer (Phase 8 / R13)
    # Recompose the system prompt before every turn so CONTEXT.md / ledger /
    # handoff updates surface mid-session (compose() otherwise runs once per
    # cached agent).
    refresh_per_turn: bool = True
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


class ComputerCapability(BaseModel):
    """Computer automation (use_computer) — screen/mouse/keyboard control.

    High-risk; OFF by default. When enabled, sensitive actions (click/type/
    hotkey/drag/…) require interactive approval unless require_approval is set
    False. Needs the ``[computer]`` extra (pyautogui).
    """

    enabled: bool = False
    require_approval: bool = True


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
    computer: ComputerCapability = ComputerCapability()


class PerformanceConfig(BaseModel):
    """Performance optimization configuration."""

    # Off by default: warm-up sends a real model request on every boot, which would
    # spend API credits/quota for no user benefit. Opt in if you want lower first-message latency.
    model_warmup: bool = False
    session_cache_size: int = 10
    embedding_cache_size: int = 100
    # Cap how much text a single tool result feeds back to the model. A command
    # that dumps thousands of lines (ruff, mypy, big greps) would otherwise blow
    # the model's context window. 0 disables the cap. ~12000 chars ≈ 3k tokens.
    max_tool_output_chars: int = 12000


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
    recordings: str = "~/.aethon/recordings"


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
    runtime_tools: RuntimeToolsConfig = RuntimeToolsConfig()
    session_recorder: SessionRecorderConfig = SessionRecorderConfig()
    ambient: AmbientConfig = AmbientConfig()
    lsp: LSPConfig = LSPConfig()
    prompt: PromptConfig = PromptConfig()
    reliability: ReliabilityConfig = ReliabilityConfig()
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
        """Write a config dict to a YAML file, creating parent dirs. Returns the path.

        Secrets hygiene (S8): the file is chmod 0600 and its parent dir 0700, so
        a config that may carry plaintext keys is never world-/group-readable.
        """
        path = Path(config_path).expanduser()
        # Only tighten a directory WE create — never clobber the perms of a
        # pre-existing (possibly shared) directory a custom --config points at.
        parent_existed = path.parent.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        # Best-effort: chmod is a no-op on filesystems that don't support it.
        try:
            os.chmod(path, 0o600)
            if not parent_existed:
                os.chmod(path.parent, 0o700)
        except OSError:
            pass
        return path
