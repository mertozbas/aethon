"""Tests for VectorMemory.

Tests that need Ollama are auto-skipped when Ollama is not running.
"""

import pytest

from aethon.memory.vector import VectorMemory


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


@pytest.mark.ollama
def test_create_memory(memory):
    """VectorMemory creates successfully with SQLite DB."""
    assert memory.count() == 0


@pytest.mark.ollama
def test_get_embedding(memory):
    """Ollama embedding returns a float list."""
    emb = memory._get_embedding("test text")
    assert isinstance(emb, list)
    assert len(emb) > 0
    assert isinstance(emb[0], float)


@pytest.mark.ollama
def test_store_and_count(memory):
    """Store increments memory count."""
    memory.store("Python 3.10+ kullan")
    assert memory.count() == 1

    memory.store("asyncio tercih et")
    assert memory.count() == 2


@pytest.mark.ollama
def test_store_returns_id(memory):
    """Store returns the memory ID."""
    mid = memory.store("Test icerik")
    assert isinstance(mid, int)
    assert mid > 0


@pytest.mark.ollama
def test_search_finds_similar(memory):
    """Semantic search returns all stored content with scores."""
    memory.store("Python programlama dili hizli ve guclu")
    memory.store("JavaScript web tarayicilarda calisir")
    memory.store("Turkiye'nin baskenti Ankara")

    results = memory.search("Python programlama dili", top_k=3)
    assert len(results) == 3
    contents = [r["content"] for r in results]
    assert "Python programlama dili hizli ve guclu" in contents
    assert all(isinstance(r["score"], float) for r in results)


@pytest.mark.ollama
def test_search_with_category(memory):
    """Category filter works in search."""
    memory.store("Python hizli", category="programming")
    memory.store("Ankara baskent", category="geography")

    results = memory.search("Python", category="programming")
    assert len(results) == 1
    assert results[0]["category"] == "programming"


@pytest.mark.ollama
def test_list_all(memory):
    """list_all returns stored memories."""
    memory.store("birinci kayit")
    memory.store("ikinci kayit")
    memory.store("ucuncu kayit")

    items = memory.list_all(limit=10)
    assert len(items) == 3
    assert items[0]["content"] == "ucuncu kayit"


@pytest.mark.ollama
def test_forget(memory):
    """forget removes a specific memory."""
    mid = memory.store("silinecek kayit")
    assert memory.count() == 1

    deleted = memory.forget(mid)
    assert deleted is True
    assert memory.count() == 0


def test_forget_nonexistent(tmp_path):
    """forget returns False for nonexistent ID (no embedding needed)."""
    db_path = str(tmp_path / "test_memory.sqlite")
    mem = VectorMemory.__new__(VectorMemory)
    mem.db_path = db_path
    mem.db = __import__("sqlite3").connect(db_path)
    mem._lock = __import__("threading").Lock()
    mem._create_tables()

    deleted = mem.forget(9999)
    assert deleted is False
    mem.close()


def test_cosine_similarity():
    """Static cosine similarity computation."""
    assert VectorMemory._cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert VectorMemory._cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert VectorMemory._cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)
    assert VectorMemory._cosine_similarity([0, 0], [1, 0]) == pytest.approx(0.0)


@pytest.mark.ollama
def test_store_with_metadata(memory):
    """Store with metadata preserves it."""
    mid = memory.store(
        "onemli bilgi",
        category="notes",
        metadata={"source": "test", "priority": "high"},
    )
    results = memory.search("onemli bilgi", top_k=1)
    assert results[0]["metadata"]["source"] == "test"
    assert results[0]["metadata"]["priority"] == "high"
