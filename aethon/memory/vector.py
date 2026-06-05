"""SQLite + multi-provider embedding based vector memory.

Provides long-term semantic memory for AETHON using embeddings
from Ollama or OpenAI, with SQLite storage and cosine similarity search.
"""

import json
import math
import sqlite3
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import requests


class VectorMemory:
    """SQLite + embedding based long-term memory.

    Supports embedding providers: ollama, openai.
    """

    def __init__(self, db_path: str, ollama_host: str = "", model_id: str = "",
                 embedding_cache_size: int = 100,
                 embedding_provider: str = "ollama",
                 embedding_api_key: str = ""):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # Serialize all access to the shared connection: writes come from the agent's
        # worker thread while reads come from the dashboard on the main loop.
        self._lock = threading.Lock()
        self.ollama_host = (ollama_host or "http://localhost:11434").rstrip("/")
        self.model_id = model_id
        self.embedding_provider = embedding_provider.lower()
        self.embedding_api_key = embedding_api_key
        self._embedding_cache_size = embedding_cache_size
        self._create_tables()

        # Create cached embedding function
        @lru_cache(maxsize=embedding_cache_size)
        def _cached_embedding(text: str) -> tuple:
            return tuple(self._get_embedding_raw(text))

        self._cached_embedding = _cached_embedding

    def _create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                embedding TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.commit()

    def store(self, content: str, category: str = "general",
              metadata: dict | None = None) -> int:
        """Store information with embedding.

        Returns:
            The ID of the stored memory.
        """
        embedding = self._get_embedding(content)
        with self._lock:
            cursor = self.db.execute(
                "INSERT INTO memories (content, category, embedding, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (content, category, json.dumps(embedding),
                 json.dumps(metadata or {}), datetime.now().isoformat()),
            )
            self.db.commit()
            return cursor.lastrowid

    def search(self, query: str, top_k: int = 5,
               category: str | None = None) -> list[dict]:
        """Semantic search using cosine similarity."""
        query_embedding = self._get_embedding(query)

        sql = "SELECT id, content, category, embedding, metadata, created_at FROM memories"
        params = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)

        with self._lock:
            rows = self.db.execute(sql, params).fetchall()

        scored = []
        for row_id, content, cat, emb_json, meta_json, created in rows:
            emb = json.loads(emb_json)
            score = self._cosine_similarity(query_embedding, emb)
            scored.append({
                "id": row_id,
                "content": content,
                "category": cat,
                "score": score,
                "metadata": json.loads(meta_json),
                "created_at": created,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def list_all(self, limit: int = 50) -> list[dict]:
        """List all memories ordered by creation date."""
        with self._lock:
            rows = self.db.execute(
                "SELECT id, content, category, created_at FROM memories "
                "ORDER BY created_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [
            {"id": r[0], "content": r[1], "category": r[2], "created_at": r[3]}
            for r in rows
        ]

    def forget(self, memory_id: int) -> bool:
        """Delete a specific memory.

        Returns:
            True if a memory was deleted, False if not found.
        """
        with self._lock:
            cursor = self.db.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,),
            )
            self.db.commit()
            return cursor.rowcount > 0

    def count(self) -> int:
        """Return total number of memories."""
        with self._lock:
            row = self.db.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0]

    def close(self):
        """Close the database connection."""
        self.db.close()

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding with LRU cache support.

        Returns list[float] from cached tuple.
        """
        return list(self._cached_embedding(text))

    def _get_embedding_raw(self, text: str) -> list[float]:
        """Get embedding from configured provider (uncached)."""
        if self.embedding_provider == "openai":
            return self._get_embedding_openai(text)
        return self._get_embedding_ollama(text)

    def _get_embedding_ollama(self, text: str) -> list[float]:
        """Get embedding from Ollama /api/embed endpoint."""
        response = requests.post(
            f"{self.ollama_host}/api/embed",
            json={"model": self.model_id, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def _get_embedding_openai(self, text: str) -> list[float]:
        """Get embedding from OpenAI embeddings API."""
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {self.embedding_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model_id, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
