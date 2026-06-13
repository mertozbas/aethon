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


def test_cosine_similarity_unequal_length_is_zero():
    """E5: unequal-length vectors are not comparable — refuse (0.0), never
    silently zip-truncate to the shorter one."""
    assert VectorMemory._cosine_similarity([1, 0], [1, 0, 0]) == 0.0
    assert VectorMemory._cosine_similarity([1, 0, 0], [1, 0]) == 0.0
    assert VectorMemory._cosine_similarity([1, 1], []) == 0.0


# --- E5.1 embedding robustness (offline — embedding stubbed, no Ollama) ---


def _offline_memory(tmp_path, vec, model_id="fake-model"):
    """A VectorMemory whose embedding is a fixed stub vector (no network).

    ``__init__`` only opens SQLite, so this stays fully offline; we then replace
    ``_get_embedding`` to control the vector (and its dimension)."""
    mem = VectorMemory(db_path=str(tmp_path / "m.sqlite"), model_id=model_id)
    mem._get_embedding = lambda text, v=list(vec): list(v)
    return mem


def test_store_records_model_and_dim(tmp_path):
    """Every stored row carries the embedding model + dimension that produced it."""
    mem = _offline_memory(tmp_path, [0.1, 0.2, 0.3], model_id="nomic-embed-text")
    mem.store("bir not")
    row = mem.db.execute(
        "SELECT embedding_model, embedding_dim FROM memories"
    ).fetchone()
    assert row == ("nomic-embed-text", 3)
    mem.close()


def test_search_skips_dim_mismatch_loudly(tmp_path, caplog):
    """A row embedded at a different dimension is skipped + logged — never fed
    into cosine where zip would silently truncate it into a corrupt score."""
    import logging

    mem = _offline_memory(tmp_path, [0.1, 0.2])      # store a 2-dim vector
    mem.store("eski model kaydı")
    # Now the model returns a 3-dim vector (as if the embedding model changed).
    mem._get_embedding = lambda text: [0.1, 0.2, 0.3]
    with caplog.at_level(logging.WARNING, logger="aethon.memory"):
        results = mem.search("sorgu", top_k=5)
    assert results == []                              # mismatched row not returned
    assert any("different dimension" in r.message for r in caplog.records)
    mem.close()


def test_search_returns_matching_dim_rows(tmp_path):
    """Same-dimension rows are still searched normally."""
    mem = _offline_memory(tmp_path, [1.0, 0.0])
    mem.store("a")
    mem.store("b")
    results = mem.search("a", top_k=5)
    assert len(results) == 2
    mem.close()


def test_migration_adds_columns_to_legacy_db(tmp_path):
    """Opening a pre-E5 DB (no model/dim columns) adds them; legacy rows whose
    columns are NULL fall back to the vector's own length and stay searchable."""
    import json
    import sqlite3

    db_path = str(tmp_path / "legacy.sqlite")
    con = sqlite3.connect(db_path)
    con.execute(
        "CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL, category TEXT DEFAULT 'general', "
        "embedding TEXT NOT NULL, metadata TEXT DEFAULT '{}', "
        "created_at TEXT NOT NULL)"
    )
    con.execute(
        "INSERT INTO memories (content, embedding, metadata, created_at) "
        "VALUES (?, ?, '{}', '2026-01-01')",
        ("eski kayıt", json.dumps([1.0, 0.0])),      # 2-dim, no dim column
    )
    con.commit()
    con.close()

    mem = VectorMemory(db_path=db_path, model_id="fake")
    cols = {r[1] for r in mem.db.execute("PRAGMA table_info(memories)")}
    assert {"embedding_model", "embedding_dim"} <= cols
    # Legacy row (NULL dim) matches a 2-dim query via its vector length.
    mem._get_embedding = lambda text: [1.0, 0.0]
    assert len(mem.search("x", top_k=5)) == 1
    # A 3-dim query skips the legacy 2-dim row.
    mem._get_embedding = lambda text: [1.0, 0.0, 0.0]
    assert mem.search("x", top_k=5) == []
    mem.close()


@pytest.mark.ollama
def test_store_with_metadata(memory):
    """Store with metadata preserves it."""
    memory.store(
        "onemli bilgi",
        category="notes",
        metadata={"source": "test", "priority": "high"},
    )
    results = memory.search("onemli bilgi", top_k=1)
    assert results[0]["metadata"]["source"] == "test"
    assert results[0]["metadata"]["priority"] == "high"
