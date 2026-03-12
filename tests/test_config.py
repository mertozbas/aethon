"""Tests for AethonConfig."""

import os
import pytest
from pathlib import Path

from aethon.config import AethonConfig, ModelConfig, MemoryConfig, ChannelsConfig


def test_config_defaults():
    """Default config loads with correct values."""
    config = AethonConfig()
    assert config.model.provider == "ollama"
    assert config.model.model_id == "qwen3-coder-next"
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
    assert config.model.provider == "ollama"


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
