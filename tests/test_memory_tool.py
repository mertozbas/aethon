"""Tests for memory tool.

Uses real Ollama with nomic-embed-text for embedding.
Tests are auto-skipped when Ollama is not running.
"""

import pytest

from aethon.memory.vector import VectorMemory
from aethon.tools.memory_tool import create_memory_tool


@pytest.fixture
def memory(tmp_path):
    """VectorMemory with real Ollama embedding."""
    db_path = str(tmp_path / "test_memory.sqlite")
    mem = VectorMemory(
        db_path=db_path,
        ollama_host="http://localhost:11434",
        model_id="nomic-embed-text",
    )
    yield mem
    mem.close()


@pytest.fixture
def memory_tool(memory):
    """Create memory tool bound to test VectorMemory."""
    return create_memory_tool(memory)


@pytest.mark.ollama
def test_create_memory_tool_returns_callable(memory):
    """create_memory_tool returns a callable."""
    tool_fn = create_memory_tool(memory)
    assert callable(tool_fn)


@pytest.mark.ollama
def test_store_action(memory_tool, memory):
    """store action saves content."""
    result = memory_tool(
        action="store",
        content="Python 3.10+ kullan",
        category="preferences",
    )
    assert "Hafizaya kaydedildi" in result
    assert "preferences" in result
    assert memory.count() == 1


@pytest.mark.ollama
def test_store_without_content(memory_tool):
    """store without content returns error."""
    result = memory_tool(
        action="store",
        content="",
    )
    assert "Hata" in result


@pytest.mark.ollama
def test_search_action(memory_tool, memory):
    """search action finds stored content."""
    memory.store("Python hizli bir dil")
    memory.store("JavaScript web dili")

    result = memory_tool(
        action="search",
        query="Python programlama",
    )
    assert "Python" in result


@pytest.mark.ollama
def test_search_without_query(memory_tool):
    """search without query returns error."""
    result = memory_tool(
        action="search",
        query="",
    )
    assert "Hata" in result


@pytest.mark.ollama
def test_list_action(memory_tool, memory):
    """list action shows memories."""
    memory.store("birinci")
    memory.store("ikinci")

    result = memory_tool(
        action="list",
    )
    assert "birinci" in result
    assert "ikinci" in result


@pytest.mark.ollama
def test_list_empty(memory_tool):
    """list on empty memory returns empty message."""
    result = memory_tool(
        action="list",
    )
    assert "bos" in result


@pytest.mark.ollama
def test_forget_action(memory_tool, memory):
    """forget action removes memory."""
    mid = memory.store("silinecek")

    result = memory_tool(
        action="forget",
        memory_id=mid,
    )
    assert "silindi" in result
    assert memory.count() == 0


@pytest.mark.ollama
def test_forget_without_id(memory_tool):
    """forget without memory_id returns error."""
    result = memory_tool(
        action="forget",
        memory_id=0,
    )
    assert "Hata" in result


@pytest.mark.ollama
def test_unknown_action(memory_tool):
    """Unknown action returns error."""
    result = memory_tool(
        action="unknown",
    )
    assert "Bilinmeyen" in result
