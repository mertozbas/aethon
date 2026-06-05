"""Tests for performance optimizations."""

import pytest
from collections import OrderedDict
from unittest.mock import MagicMock, patch

from aethon.config import AethonConfig, PathsConfig, ModelConfig, PerformanceConfig


@pytest.fixture
def small_cache_config(tmp_path):
    """Config with small session cache for testing eviction."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "SOUL.md").write_text("Test")
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    return AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        performance=PerformanceConfig(session_cache_size=3),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(sessions),
            logs=str(logs),
            memory_db=str(tmp_path / "memory.sqlite"),
            credentials=str(tmp_path / "credentials"),
        ),
    )


def test_runtime_uses_ordered_dict(small_cache_config):
    """Runtime agents dict is OrderedDict for LRU."""
    from aethon.agent.runtime import AethonRuntime

    runtime = AethonRuntime(small_cache_config)
    assert isinstance(runtime.agents, OrderedDict)


def test_session_lru_eviction(small_cache_config):
    """Oldest session is evicted when cache is full."""
    from aethon.agent.runtime import AethonRuntime

    runtime = AethonRuntime(small_cache_config)

    # Create 3 sessions (cache_size = 3)
    runtime.get_or_create_agent("s1")
    runtime.get_or_create_agent("s2")
    runtime.get_or_create_agent("s3")
    assert len(runtime.agents) == 3

    # Creating 4th should evict s1 (oldest)
    runtime.get_or_create_agent("s4")
    assert len(runtime.agents) == 3
    assert "s1" not in runtime.agents
    assert "s4" in runtime.agents


def test_session_lru_access_refreshes(small_cache_config):
    """Accessing a session moves it to end (refreshes)."""
    from aethon.agent.runtime import AethonRuntime

    runtime = AethonRuntime(small_cache_config)

    runtime.get_or_create_agent("s1")
    runtime.get_or_create_agent("s2")
    runtime.get_or_create_agent("s3")

    # Access s1 — moves it to end, s2 becomes oldest
    runtime.get_or_create_agent("s1")

    # Creating s4 should evict s2 (now oldest)
    runtime.get_or_create_agent("s4")
    assert "s1" in runtime.agents
    assert "s2" not in runtime.agents
    assert "s4" in runtime.agents


def test_session_same_agent_returned(small_cache_config):
    """Same session returns same agent instance."""
    from aethon.agent.runtime import AethonRuntime

    runtime = AethonRuntime(small_cache_config)

    a1 = runtime.get_or_create_agent("s1")
    a2 = runtime.get_or_create_agent("s1")
    assert a1 is a2


def test_embedding_cache(tmp_path):
    """VectorMemory uses LRU cache for embeddings."""
    from aethon.memory.vector import VectorMemory

    call_count = 0
    original_post = None

    def mock_post(url, json=None, timeout=None):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        resp.raise_for_status = MagicMock()
        return resp

    db_path = str(tmp_path / "test_cache.sqlite")

    with patch("aethon.memory.vector.requests.post", side_effect=mock_post):
        memory = VectorMemory(
            db_path=db_path,
            ollama_host="http://localhost:11434",
            model_id="test-model",
            embedding_cache_size=10,
        )
        # First call — hits API
        emb1 = memory._get_embedding("hello")
        assert call_count == 1

        # Second call same text — should use cache
        emb2 = memory._get_embedding("hello")
        assert call_count == 1  # No additional API call

        # Different text — hits API
        emb3 = memory._get_embedding("world")
        assert call_count == 2

        # Results should be equal
        assert emb1 == emb2


def test_warm_up_method_exists(small_cache_config):
    """Runtime has warm_up method."""
    from aethon.agent.runtime import AethonRuntime

    runtime = AethonRuntime(small_cache_config)
    assert hasattr(runtime, "warm_up")
    assert callable(runtime.warm_up)
