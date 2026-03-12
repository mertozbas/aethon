"""Tests for AethonRuntime."""

import pytest

from aethon.config import AethonConfig, PathsConfig, ModelConfig
from aethon.agent.runtime import AethonRuntime
from aethon.channels.base import InboundMessage


@pytest.fixture
def runtime_config(tmp_path):
    """Config with temp workspace for runtime tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test kisilik")
    (workspace / "TOOLS.md").write_text("Test tercihler")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    return AethonConfig(
        model=ModelConfig(provider="ollama", model_id="qwen3-coder-next"),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )


def test_runtime_creation(runtime_config):
    """AethonRuntime creates without errors."""
    runtime = AethonRuntime(runtime_config)
    assert runtime.model is not None
    assert runtime.prompt_composer is not None
    assert runtime.agents == {}


def test_get_or_create_agent(runtime_config):
    """Agent is created for a session."""
    runtime = AethonRuntime(runtime_config)
    agent = runtime.get_or_create_agent("test-session")
    assert agent is not None
    assert "test-session" in runtime.agents


def test_same_session_same_agent(runtime_config):
    """Same session returns same agent instance."""
    runtime = AethonRuntime(runtime_config)
    agent1 = runtime.get_or_create_agent("session-1")
    agent2 = runtime.get_or_create_agent("session-1")
    assert agent1 is agent2


def test_different_session_different_agent(runtime_config):
    """Different sessions return different agents."""
    runtime = AethonRuntime(runtime_config)
    agent1 = runtime.get_or_create_agent("session-1")
    agent2 = runtime.get_or_create_agent("session-2")
    assert agent1 is not agent2
    assert len(runtime.agents) == 2


def test_tools_list(runtime_config):
    """Runtime provides Phase 1 tools."""
    runtime = AethonRuntime(runtime_config)
    tools = runtime._get_tools()
    assert len(tools) > 0
    tool_names = [getattr(t, "__name__", str(t)) for t in tools]
    assert any("file_read" in name for name in tool_names)


def test_hooks_list(runtime_config):
    """Runtime provides security hooks."""
    runtime = AethonRuntime(runtime_config)
    hooks = runtime._get_hooks()
    assert len(hooks) > 0
    from aethon.agent.hooks.security import SecurityHookProvider
    assert isinstance(hooks[0], SecurityHookProvider)


@pytest.mark.asyncio
async def test_process_returns_response(runtime_config):
    """Process method returns a string response from real Ollama model."""
    runtime = AethonRuntime(runtime_config)
    msg = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Merhaba, 2+2 kac yapar? Sadece sayiyi soyler misin?",
    )
    response = await runtime.process(msg, "test-session")
    assert isinstance(response, str)
    assert len(response) > 0
