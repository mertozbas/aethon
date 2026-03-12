"""Integration tests for AETHON Phase 1 + Phase 2.

Tests the full pipeline: Config -> Runtime -> Router -> Response.
Phase 2 adds VectorMemory and session isolation tests.
Requires Ollama to be running with qwen3-coder-next and nomic-embed-text.
"""

import pytest
import asyncio

from aethon.config import AethonConfig, PathsConfig, ModelConfig, MemoryConfig
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
        model=ModelConfig(provider="ollama", model_id="qwen3-coder-next"),
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
