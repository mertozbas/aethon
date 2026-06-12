"""Tests for dynamic specialist creation (Phase 10 C5)."""

import json

import pytest

from aethon.agent.fake_model import EchoModel
from aethon.agent.specialists import (
    DYNAMIC_TOOL_ALLOWLIST,
    SPECIALIST_CONFIGS,
    SpecialistFactory,
)


def _factory(tmp_path):
    return SpecialistFactory(EchoModel(), workspace=str(tmp_path))


def test_add_specialist_persists_and_registers(tmp_path):
    f = _factory(tmp_path)
    key = f.add_specialist("DB Expert", "You know databases.", ["file_read", "think"])
    assert key == "dbexpert"                         # slugged
    assert key in f.list_specialists()
    assert f.list_specialists()[key] == "custom"
    # Persisted to workspace/specialists/<key>.json with tool NAMES.
    saved = json.loads((tmp_path / "specialists" / "dbexpert.json").read_text())
    assert saved["tools"] == ["file_read", "think"]
    assert "databases" in saved["system_prompt"]


def test_dynamic_specialist_loads_across_sessions(tmp_path):
    _factory(tmp_path).add_specialist("Scribe", "Write notes.", ["file_write", "think"])
    # A fresh factory (≈ restart) loads the persisted specialist from disk.
    fresh = _factory(tmp_path)
    assert "scribe" in fresh.list_specialists()
    agent = fresh.get("scribe")                       # invokable
    assert agent is not None


def test_tool_names_resolved_only_through_allowlist(tmp_path):
    """Security: an unknown/dangerous tool name is dropped, never imported."""
    f = _factory(tmp_path)
    f.add_specialist("Sneaky", "x", ["file_read", "os.system", "subprocess", "rm"])
    saved = json.loads((tmp_path / "specialists" / "sneaky.json").read_text())
    assert saved["tools"] == ["file_read"]            # only the allowlisted one kept
    # And every persisted name is in the allowlist.
    assert all(t in DYNAMIC_TOOL_ALLOWLIST for t in saved["tools"])


def test_name_is_slugged_no_path_traversal(tmp_path):
    f = _factory(tmp_path)
    key = f.add_specialist("../../etc/passwd", "x", ["think"])
    assert "/" not in key and ".." not in key
    # The file lands inside the specialists dir, not outside.
    assert (tmp_path / "specialists" / f"{key}.json").exists()


def test_specialist_always_has_a_tool(tmp_path):
    f = _factory(tmp_path)
    f.add_specialist("Empty", "x", [])                # no tools requested
    saved_cfg = f._dynamic["empty"]
    assert len(saved_cfg["tools"]) >= 1               # falls back to think


def test_remove_specialist(tmp_path):
    f = _factory(tmp_path)
    f.add_specialist("Temp", "x", ["think"])
    assert f.remove_specialist("Temp") is True
    assert "temp" not in f.list_specialists()
    assert not (tmp_path / "specialists" / "temp.json").exists()
    assert f.remove_specialist("nope") is False


def test_unknown_specialist_still_raises(tmp_path):
    f = _factory(tmp_path)
    with pytest.raises(ValueError):
        f.get("does-not-exist")


def test_builtins_still_present(tmp_path):
    f = _factory(tmp_path)
    listing = f.list_specialists()
    for name in SPECIALIST_CONFIGS:
        assert listing[name] == "built-in"


def test_corrupt_specialist_file_skipped_not_crash(tmp_path):
    d = tmp_path / "specialists"
    d.mkdir()
    (d / "bad.json").write_text("{not json", encoding="utf-8")
    (d / "good.json").write_text(
        json.dumps({"name": "good", "system_prompt": "x", "tools": ["think"]}),
        encoding="utf-8",
    )
    f = _factory(tmp_path)
    assert "good" in f.list_specialists()
    assert "bad" not in f.list_specialists()
