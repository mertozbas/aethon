"""Integration tests for AETHON Phase 1 + Phase 2 + Phase 3 + Phase 4.

Tests the full pipeline: Config -> Runtime -> Router -> Response.
Phase 2 adds VectorMemory and session isolation tests.
Phase 4 adds TelemetryHook, MemoryGuard, Context, Scheduler, Dashboard tests.
Requires Ollama to be running with qwen3-coder-next and nomic-embed-text.
"""

import pytest
import asyncio

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig,
    MultiAgentConfig, SOPConfig, TelemetryConfig, MemoryGuardConfig,
    SchedulerConfig, DashboardConfig, WebhookConfig, PerformanceConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.gateway.router import MessageRouter
from aethon.channels.base import InboundMessage


@pytest.fixture
def integration_setup(tmp_path):
    """Full setup for integration tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text(
        "Sen AETHON, kisa ve oz yanit veren bir AI asistansin."
    )
    (workspace / "TOOLS.md").write_text("Turkce yanit ver.")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(
            enabled=True,
            embedding_model="nomic-embed-text",
            db_path=str(tmp_path / "memory.sqlite"),
        ),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )

    runtime = AethonRuntime(config)
    router = MessageRouter(config, runtime)
    return config, runtime, router


@pytest.mark.ollama
@pytest.mark.asyncio
async def test_full_pipeline(integration_setup):
    """Full message pipeline: InboundMessage -> Router -> Agent -> Response."""
    config, runtime, router = integration_setup

    msg = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Merhaba, 1+1 kac yapar? Sadece sayiyi soyler misin?",
    )

    response = await router.handle(msg)

    assert response is not None
    assert response.channel == "cli"
    assert response.recipient_id == "local"
    assert isinstance(response.text, str)
    assert len(response.text) > 0


@pytest.mark.ollama
@pytest.mark.asyncio
async def test_session_persistence(integration_setup):
    """Same session maintains conversation context."""
    config, runtime, router = integration_setup

    msg1 = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Benim adim Mert.",
    )
    await router.handle(msg1)

    msg2 = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Benim adim neydi?",
    )
    response = await router.handle(msg2)

    assert response is not None
    assert isinstance(response.text, str)
    # Agent should remember the name from same session


@pytest.mark.ollama
@pytest.mark.asyncio
async def test_session_isolation(integration_setup):
    """Different channels have isolated sessions."""
    config, runtime, router = integration_setup

    # CLI user says name
    msg1 = InboundMessage(
        channel="cli",
        sender_id="local",
        sender_name="User",
        text="Benim adim Ali.",
    )
    await router.handle(msg1)

    # WebChat user asks — different session
    msg2 = InboundMessage(
        channel="webchat",
        sender_id="remote",
        sender_name="WebUser",
        text="Benim adim neydi?",
    )
    response = await router.handle(msg2)

    assert response is not None
    assert isinstance(response.text, str)
    # WebChat session should NOT know about CLI session's name


@pytest.mark.asyncio
async def test_runtime_has_memory(integration_setup):
    """Runtime creates VectorMemory when enabled."""
    config, runtime, router = integration_setup

    assert runtime.memory is not None
    assert runtime.memory.count() == 0


@pytest.mark.asyncio
async def test_runtime_tools_include_memory(integration_setup):
    """Runtime tools include manage_memory when memory is active."""
    config, runtime, router = integration_setup

    tools = runtime._get_tools()
    tool_names = [getattr(t, "__name__", str(t)) for t in tools]
    assert any("memory" in name.lower() for name in tool_names)


@pytest.mark.ollama
@pytest.mark.asyncio
async def test_vector_memory_direct(integration_setup):
    """VectorMemory store + search works end-to-end."""
    config, runtime, router = integration_setup

    memory = runtime.memory
    mid = memory.store("Python programlama dili ogren", category="learning")
    assert mid > 0

    results = memory.search("Python nedir?", top_k=1)
    assert len(results) == 1
    assert "Python" in results[0]["content"]

    items = memory.list_all()
    assert len(items) == 1

    deleted = memory.forget(mid)
    assert deleted is True
    assert memory.count() == 0


# --- Phase 3 Integration Tests ---


@pytest.fixture
def phase3_setup(tmp_path):
    """Full setup for Phase 3 integration tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text(
        "Sen AETHON, kisa ve oz yanit veren bir AI asistansin."
    )
    (workspace / "TOOLS.md").write_text("Turkce yanit ver.")
    sops_dir = workspace / "sops"
    sops_dir.mkdir()
    (sops_dir / "test-sop.sop.md").write_text(
        "# Test SOP\n\n## Overview\nTest SOP aciklamasi.\n\n"
        "## Steps\nKullaniciya 'Test SOP calisti' de.\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(
            enabled=True,
            embedding_model="nomic-embed-text",
            db_path=str(tmp_path / "memory.sqlite"),
        ),
        multi_agent=MultiAgentConfig(enabled=True),
        sops=SOPConfig(enabled=True, builtin_sops_enabled=True),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )

    runtime = AethonRuntime(config)
    router = MessageRouter(config, runtime)
    return config, runtime, router


@pytest.mark.asyncio
async def test_runtime_has_specialist_factory(phase3_setup):
    """Runtime creates SpecialistFactory when multi_agent enabled."""
    config, runtime, router = phase3_setup
    assert runtime.specialist_factory is not None


@pytest.mark.asyncio
async def test_runtime_has_sop_runner(phase3_setup):
    """Runtime creates SOPRunner when sops enabled."""
    config, runtime, router = phase3_setup
    assert runtime.sop_runner is not None


@pytest.mark.asyncio
async def test_sop_list_includes_builtins(phase3_setup):
    """SOP list includes built-in SOPs."""
    config, runtime, router = phase3_setup
    sops = runtime.sop_runner.list_sops()
    names = [s["name"] for s in sops]
    assert "code-assist" in names
    assert "pdd" in names


@pytest.mark.asyncio
async def test_sop_list_includes_custom(phase3_setup):
    """SOP list includes custom SOPs."""
    config, runtime, router = phase3_setup
    sops = runtime.sop_runner.list_sops()
    names = [s["name"] for s in sops]
    assert "test-sop" in names


@pytest.mark.asyncio
async def test_custom_sop_command_detected(phase3_setup):
    """Custom SOP command is detected by is_sop_command."""
    config, runtime, router = phase3_setup
    is_sop, name, user_input = runtime.sop_runner.is_sop_command("/test-sop merhaba")
    assert is_sop is True
    assert name == "test-sop"
    assert user_input == "merhaba"


@pytest.mark.asyncio
async def test_delegate_tools_in_runtime(phase3_setup):
    """Runtime tools include delegate tools."""
    config, runtime, router = phase3_setup
    tools = runtime._get_tools()
    tool_names = [
        getattr(t, "__name__", getattr(t, "tool_name", str(t)))
        for t in tools
    ]
    assert any("ask_coder" in str(n) for n in tool_names)
    assert any("ask_researcher" in str(n) for n in tool_names)
    assert any("ask_analyst" in str(n) for n in tool_names)
    assert any("ask_planner" in str(n) for n in tool_names)


# --- Phase 4 Integration Tests ---


@pytest.fixture
def phase4_setup(tmp_path):
    """Full setup for Phase 4 integration tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text(
        "Sen AETHON, kisa ve oz yanit veren bir AI asistansin."
    )
    (workspace / "TOOLS.md").write_text("Turkce yanit ver.")
    (workspace / "CONTEXT.md").write_text("# Mevcut Baglam\n\nTest baglami.\n")
    sops_dir = workspace / "sops"
    sops_dir.mkdir()
    (sops_dir / "test-sop.sop.md").write_text(
        "# Test SOP\n\n## Overview\nTest SOP.\n\n## Steps\nTest.\n"
    )
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(
            enabled=True,
            embedding_model="nomic-embed-text",
            db_path=str(tmp_path / "memory.sqlite"),
        ),
        multi_agent=MultiAgentConfig(enabled=True),
        sops=SOPConfig(enabled=True, builtin_sops_enabled=True),
        telemetry=TelemetryConfig(enabled=True, max_history=1000),
        memory_guard=MemoryGuardConfig(enabled=True),
        scheduler=SchedulerConfig(enabled=True),
        dashboard=DashboardConfig(enabled=True),
        webhook=WebhookConfig(enabled=True),
        performance=PerformanceConfig(
            session_cache_size=5,
            embedding_cache_size=50,
        ),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )

    runtime = AethonRuntime(config)
    return config, runtime


@pytest.mark.asyncio
async def test_runtime_has_telemetry_hook(phase4_setup):
    """Runtime creates TelemetryHook when telemetry enabled."""
    config, runtime = phase4_setup
    assert runtime._telemetry_hook is not None
    assert hasattr(runtime._telemetry_hook, "get_summary")
    assert hasattr(runtime._telemetry_hook, "get_metrics")


@pytest.mark.asyncio
async def test_runtime_hooks_include_telemetry(phase4_setup):
    """Runtime hooks include TelemetryHook."""
    config, runtime = phase4_setup
    hooks = runtime._get_hooks()
    hook_types = [type(h).__name__ for h in hooks]
    assert "TelemetryHookProvider" in hook_types


@pytest.mark.asyncio
async def test_runtime_hooks_include_memory_guard(phase4_setup):
    """Runtime hooks include MemoryGuardHook."""
    config, runtime = phase4_setup
    hooks = runtime._get_hooks()
    hook_types = [type(h).__name__ for h in hooks]
    assert "MemoryGuardHookProvider" in hook_types


@pytest.mark.asyncio
async def test_runtime_has_context_updater(phase4_setup):
    """Runtime creates ContextUpdater."""
    config, runtime = phase4_setup
    assert runtime._context_updater is not None


@pytest.mark.asyncio
async def test_runtime_tools_include_context(phase4_setup):
    """Runtime tools include update_context."""
    config, runtime = phase4_setup
    tools = runtime._get_tools()
    tool_names = [
        getattr(t, "__name__", getattr(t, "tool_name", str(t)))
        for t in tools
    ]
    assert any("context" in str(n).lower() for n in tool_names)


@pytest.mark.asyncio
async def test_runtime_tools_include_send_message(phase4_setup):
    """Runtime tools include send_message."""
    config, runtime = phase4_setup
    tools = runtime._get_tools()
    tool_names = [
        getattr(t, "__name__", getattr(t, "tool_name", str(t)))
        for t in tools
    ]
    assert any("send_message" in str(n) for n in tool_names)
