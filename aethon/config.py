"""AETHON configuration system.

YAML config loading with environment variable resolution and Pydantic validation.
"""

from pathlib import Path
from typing import Optional

import os
import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model provider configuration."""

    provider: str = "ollama"
    host: str = "http://localhost:11434"
    model_id: str = "qwen3-coder-next"
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
    embedding_model: str = "nomic-embed-text"
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
