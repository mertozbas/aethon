"""Tests for AethonConfig."""

import os
import pytest
from pathlib import Path

from aethon.config import (
    AethonConfig, ModelConfig, MemoryConfig, ChannelsConfig,
    MultiAgentConfig, SOPConfig, ApprovalConfig,
    TelemetryConfig, MemoryGuardConfig, SchedulerConfig,
    DashboardConfig, WebhookConfig, MCPConfig, PerformanceConfig,
)


def test_config_defaults():
    """Default config loads with correct values."""
    config = AethonConfig()
    assert config.model.provider == "meridian"
    assert config.model.model_id == "claude-opus-4-8"
    assert config.model.temperature == 1.0
    assert config.model.top_p == 0.95
    assert config.model.top_k == 40
    assert config.model.max_tokens == 8192
    assert config.channels.webchat.port == 18790
    assert config.channels.cli.enabled is True
    assert config.channels.webchat.enabled is True
    assert config.channels.telegram.enabled is False


def test_config_env_resolve():
    """Environment variable resolution works."""
    os.environ["TEST_AETHON_TOKEN"] = "abc123"
    result = AethonConfig._resolve_env_vars("${TEST_AETHON_TOKEN}")
    assert result == "abc123"
    del os.environ["TEST_AETHON_TOKEN"]


def test_config_env_resolve_missing():
    """Missing env var resolves to empty string."""
    result = AethonConfig._resolve_env_vars("${NONEXISTENT_VAR_12345}")
    assert result == ""


def test_config_env_resolve_nested():
    """Nested dicts and lists are resolved."""
    os.environ["TEST_NESTED"] = "value123"
    data = {"key": "${TEST_NESTED}", "list": ["${TEST_NESTED}", "plain"]}
    result = AethonConfig._resolve_env_vars(data)
    assert result["key"] == "value123"
    assert result["list"][0] == "value123"
    assert result["list"][1] == "plain"
    del os.environ["TEST_NESTED"]


def test_config_load_from_yaml(tmp_path):
    """Config loads from YAML file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "model:\n"
        "  provider: openai\n"
        "  model_id: gpt-4o\n"
        "  api_key: sk-test123\n"
        "channels:\n"
        "  webchat:\n"
        "    port: 9999\n"
    )
    config = AethonConfig.load(str(config_file))
    assert config.model.provider == "openai"
    assert config.model.model_id == "gpt-4o"
    assert config.model.api_key == "sk-test123"
    assert config.channels.webchat.port == 9999


def test_config_load_nonexistent():
    """Missing config file returns defaults."""
    config = AethonConfig.load("/tmp/nonexistent_aethon_config.yaml")
    assert config.model.provider == "meridian"


def test_config_security_defaults():
    """Security config has expected defaults."""
    config = AethonConfig()
    assert "shell" in config.security.require_approval
    assert "rm -rf /" in config.security.blocked_commands
    assert config.security.workspace_only is True


def test_model_config_custom():
    """Custom model config works."""
    mc = ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        api_key="sk-ant-test",
        max_tokens=4096,
    )
    assert mc.provider == "anthropic"
    assert mc.api_key == "sk-ant-test"
    assert mc.max_tokens == 4096


def test_memory_config_defaults():
    """MemoryConfig has correct defaults."""
    config = AethonConfig()
    assert config.memory.enabled is True
    assert config.memory.embedding_model == "nomic-embed-text"
    assert config.memory.db_path == "~/.aethon/memory.sqlite"


def test_memory_config_custom():
    """Custom MemoryConfig works."""
    mc = MemoryConfig(
        enabled=False,
        embedding_model="custom-embed",
        db_path="/tmp/custom.sqlite",
    )
    assert mc.enabled is False
    assert mc.embedding_model == "custom-embed"


def test_config_with_memory_yaml(tmp_path):
    """Config loads memory section from YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "memory:\n"
        "  enabled: true\n"
        "  embedding_model: nomic-embed-text\n"
        "  db_path: /tmp/test_mem.sqlite\n"
    )
    config = AethonConfig.load(str(config_file))
    assert config.memory.enabled is True
    assert config.memory.db_path == "/tmp/test_mem.sqlite"


def test_multi_agent_config_defaults():
    """MultiAgentConfig has correct defaults."""
    config = AethonConfig()
    assert config.multi_agent.enabled is True
    assert config.multi_agent.max_handoffs == 10
    assert config.multi_agent.max_iterations == 10
    assert config.multi_agent.execution_timeout == 300.0
    assert config.multi_agent.node_timeout == 120.0


def test_multi_agent_config_custom():
    """Custom MultiAgentConfig works."""
    mc = MultiAgentConfig(
        enabled=False,
        max_handoffs=5,
        execution_timeout=60.0,
    )
    assert mc.enabled is False
    assert mc.max_handoffs == 5
    assert mc.execution_timeout == 60.0


def test_sop_config_defaults():
    """SOPConfig has correct defaults."""
    config = AethonConfig()
    assert config.sops.enabled is True
    assert config.sops.builtin_sops_enabled is True


def test_sop_config_custom():
    """Custom SOPConfig works."""
    sc = SOPConfig(enabled=False, builtin_sops_enabled=False)
    assert sc.enabled is False
    assert sc.builtin_sops_enabled is False


def test_approval_config_defaults():
    """ApprovalConfig has correct defaults (disabled by default)."""
    config = AethonConfig()
    assert config.approval.enabled is False
    assert "shell" in config.approval.requires_approval
    assert "file_write" in config.approval.requires_approval


def test_approval_config_custom():
    """Custom ApprovalConfig works."""
    ac = ApprovalConfig(
        enabled=True,
        requires_approval=["http_request"],
    )
    assert ac.enabled is True
    assert "http_request" in ac.requires_approval


def test_config_with_multi_agent_yaml(tmp_path):
    """Config loads multi_agent section from YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "multi_agent:\n"
        "  enabled: false\n"
        "  max_handoffs: 3\n"
    )
    config = AethonConfig.load(str(config_file))
    assert config.multi_agent.enabled is False
    assert config.multi_agent.max_handoffs == 3


# --- Phase 4 Config Tests ---


def test_telemetry_config_defaults():
    """TelemetryConfig has correct defaults."""
    config = AethonConfig()
    assert config.telemetry.enabled is True
    assert config.telemetry.max_history == 10000


def test_telemetry_config_custom():
    """Custom TelemetryConfig works."""
    tc = TelemetryConfig(enabled=False, max_history=500)
    assert tc.enabled is False
    assert tc.max_history == 500


def test_memory_guard_config_defaults():
    """MemoryGuardConfig has correct defaults."""
    config = AethonConfig()
    assert config.memory_guard.enabled is True
    assert config.memory_guard.custom_patterns == []


def test_memory_guard_config_custom():
    """Custom MemoryGuardConfig works."""
    mc = MemoryGuardConfig(
        enabled=True,
        custom_patterns=[r"custom_secret=\S+"],
    )
    assert mc.custom_patterns == [r"custom_secret=\S+"]


def test_scheduler_config_defaults():
    """SchedulerConfig has correct defaults."""
    config = AethonConfig()
    assert config.scheduler.enabled is True
    assert config.scheduler.default_channel == "cli"
    assert config.scheduler.jobs == {}


def test_scheduler_config_custom():
    """Custom SchedulerConfig works."""
    sc = SchedulerConfig(
        enabled=True,
        default_channel="slack",
        jobs={"morning": {"cron": "0 9 * * 1-5", "sop": "morning-brief"}},
    )
    assert sc.default_channel == "slack"
    assert "morning" in sc.jobs


def test_dashboard_config_defaults():
    """DashboardConfig has correct defaults."""
    config = AethonConfig()
    assert config.dashboard.enabled is True


def test_dashboard_config_custom():
    """Custom DashboardConfig works."""
    dc = DashboardConfig(enabled=False)
    assert dc.enabled is False


def test_webhook_config_defaults():
    """WebhookConfig has correct defaults."""
    config = AethonConfig()
    assert config.webhook.enabled is True
    assert config.webhook.secret == ""


def test_webhook_config_custom():
    """Custom WebhookConfig works."""
    wc = WebhookConfig(enabled=True, secret="my-secret-key")
    assert wc.secret == "my-secret-key"


def test_mcp_config_defaults():
    """MCPConfig has correct defaults (disabled by default)."""
    config = AethonConfig()
    assert config.mcp.enabled is False
    assert config.mcp.servers == []


def test_mcp_config_custom():
    """Custom MCPConfig works."""
    mc = MCPConfig(
        enabled=True,
        servers=[{"name": "test", "command": "python", "args": ["-m", "server"]}],
    )
    assert mc.enabled is True
    assert len(mc.servers) == 1
    assert mc.servers[0]["name"] == "test"


def test_performance_config_defaults():
    """PerformanceConfig has correct defaults."""
    config = AethonConfig()
    assert config.performance.model_warmup is False  # opt-in (avoids quota burn on boot)
    assert config.performance.session_cache_size == 10
    assert config.performance.embedding_cache_size == 100


def test_performance_config_custom():
    """Custom PerformanceConfig works."""
    pc = PerformanceConfig(
        model_warmup=False,
        session_cache_size=5,
        embedding_cache_size=50,
    )
    assert pc.model_warmup is False
    assert pc.session_cache_size == 5


def test_config_with_phase4_yaml(tmp_path):
    """Config loads Phase 4 sections from YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "telemetry:\n"
        "  enabled: true\n"
        "  max_history: 5000\n"
        "scheduler:\n"
        "  enabled: true\n"
        "  default_channel: discord\n"
        "  jobs:\n"
        "    morning:\n"
        "      cron: '0 9 * * 1-5'\n"
        "      sop: morning-brief\n"
        "mcp:\n"
        "  enabled: true\n"
        "  servers:\n"
        "    - name: custom\n"
        "      command: python\n"
    )
    config = AethonConfig.load(str(config_file))
    assert config.telemetry.max_history == 5000
    assert config.scheduler.default_channel == "discord"
    assert "morning" in config.scheduler.jobs
    assert config.mcp.enabled is True
