"""Repo map + file-summary cache (Phase 10 E3).

When the agent reads a file, we cache a compact summary beside it —
``path → {hash, purpose, symbols}`` — in ``workspace/REPO_MAP.json``. The next
session injects the MAP (a few lines per file), not the files themselves, so the
agent is oriented without re-reading; a file is only worth re-reading when its
content hash has changed. Cheap, deterministic extraction (``ast`` for Python, a
first-line fallback otherwise) — no model call. Embeddings would be lossy
semantic compression; this stores the minimal facts and lets recall be exact.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aethon.repo_map")


def _flatten(value: str) -> str:
    """Collapse whitespace — summaries reach the system prompt, and embedded
    newlines could fabricate prompt layers."""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_summary(path: Path, text: str) -> dict:
    """A file's purpose + top-level symbols, deterministically and cheaply."""
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
            purpose = _flatten((ast.get_docstring(tree) or "").split("\n", 1)[0])
            symbols = [
                n.name for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
            return {"purpose": purpose or "(python module)", "symbols": symbols}
        except (SyntaxError, ValueError):
            pass  # fall through to the generic summary
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return {"purpose": _flatten(first)[:120] or f"({path.suffix or 'file'})", "symbols": []}


class RepoMap:
    """Durable ``path → summary`` cache for files the agent has read (bounded to
    the most-recently-seen ``max_files``; older entries are discarded)."""

    def __init__(self, workspace_dir: str, max_files: int = 100, max_file_bytes: int = 200_000):
        self.workspace = Path(workspace_dir).expanduser().resolve()
        self.map_file = self.workspace / "REPO_MAP.json"
        self._lock = threading.Lock()
        self._max_files = max(1, int(max_files))
        self._max_file_bytes = max(1, int(max_file_bytes))

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _load(self) -> dict:
        if not self.map_file.exists():
            return {}
        try:
            data = json.loads(self.map_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as e:
            # Quarantine instead of silently clobbering (the one durable record).
            quarantine = self.map_file.with_name(self.map_file.name + ".corrupt")
            try:
                self.map_file.replace(quarantine)
                logger.error(f"Repo map unreadable ({e}); quarantined to {quarantine.name}.")
            except OSError:
                pass
            return {}

    def _save(self, entries: dict) -> None:
        tmp = self.map_file.with_name(f".{self.map_file.name}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.map_file)

    def observe(self, file_path: str) -> bool:
        """Record (or refresh) a file the agent just read. Returns True if the
        map changed. Silently ignores anything that isn't a mappable workspace
        file (outside the workspace, missing, too big, unreadable)."""
        try:
            p = Path(file_path).expanduser().resolve()
            rel = str(p.relative_to(self.workspace))   # raises if outside workspace
        except (ValueError, OSError, RuntimeError):
            return False
        if rel == "REPO_MAP.json" or not p.is_file():
            return False
        try:
            if p.stat().st_size > self._max_file_bytes:
                return False
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False

        h = hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:12]
        with self._lock:
            entries = self._load()
            prev = entries.pop(rel, None)  # pop so re-insert moves it to most-recent
            if prev and prev.get("hash") == h:
                prev["seen"] = self._now()
                entries[rel] = prev          # unchanged — just bump recency
                changed = False
            else:
                info = extract_summary(p, text)
                entries[rel] = {
                    "hash": h,
                    "purpose": info["purpose"],
                    "symbols": info["symbols"][:25],
                    "seen": self._now(),
                }
                changed = True
            # Cap to the most-recently-seen N (dict preserves insertion order).
            if len(entries) > self._max_files:
                for k in list(entries)[: len(entries) - self._max_files]:
                    entries.pop(k, None)
                changed = True
            self._save(entries)
        return changed

    def snapshot(self, max_files: int = 50, max_chars: int = 2000) -> str:
        """A compact markdown map of the most-recently-seen files (newest last),
        for the system-prompt layer. Empty string when the map is empty.

        Files that no longer exist on disk are omitted (so a deleted file doesn't
        masquerade as current), and every rendered field is flattened — a
        hand-edited / externally-written REPO_MAP.json must not be able to inject
        a prompt layer through a symbol or purpose string."""
        entries = self._load()
        if not entries:
            return ""
        items = list(entries.items())[-max_files:]
        lines = []
        for rel, info in items:
            if not isinstance(info, dict) or not (self.workspace / rel).exists():
                continue  # gone from disk → don't show it as current
            line = f"- {_flatten(rel)}"
            purpose = _flatten(str(info.get("purpose", "")))
            if purpose:
                line += f" — {purpose}"
            symbols = info.get("symbols") or []
            if isinstance(symbols, list) and symbols:
                rendered = ", ".join(_flatten(str(s)) for s in symbols[:12])
                line += f"  [{rendered}]"
            lines.append(line)
        out = "\n".join(lines)
        return out[:max_chars]
