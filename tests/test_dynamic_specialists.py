"""Tests for dynamic specialist creation (Phase 10 C5)."""

import json

import pytest

from aethon.agent.fake_model import EchoModel
from aethon.agent.specialists import (
    DYNAMIC_TOOL_ALLOWLIST,
    SPECIALIST_CONFIGS,
    SpecialistFactory,
)


def _factory(tmp_path, allow_powerful=False):
    return SpecialistFactory(
        EchoModel(), workspace=str(tmp_path), allow_powerful=allow_powerful
    )


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


# --- manage_specialists tool ---


def test_manage_specialists_create_and_list(tmp_path):
    from aethon.tools.specialist_tool import create_manage_specialists_tool

    f = _factory(tmp_path)
    tool = create_manage_specialists_tool(f, allow_powerful=False)
    out = tool._tool_func(action="create", name="DB Guru", system_prompt="dbs",
                          tools="file_read, think")
    assert "dbguru" in out
    assert "dbguru" in f.list_specialists()
    listed = tool._tool_func(action="list")
    assert "dbguru (custom)" in listed
    assert "coder (built-in)" in listed


def test_manage_specialists_rejects_unknown_tool(tmp_path):
    from aethon.tools.specialist_tool import create_manage_specialists_tool

    tool = create_manage_specialists_tool(_factory(tmp_path), allow_powerful=False)
    out = tool._tool_func(action="create", name="x", system_prompt="p",
                          tools="file_read, os.system")
    assert "not allowed" in out and "os.system" in out


def test_manage_specialists_powerful_gated(tmp_path):
    import strands_tools
    from aethon.tools.specialist_tool import create_manage_specialists_tool

    # allow_powerful=False on both factory + tool: shell AND python_repl refused.
    f = _factory(tmp_path, allow_powerful=False)
    blocked = create_manage_specialists_tool(f, allow_powerful=False)
    for bad in ("shell", "python_repl", "file_write"):
        out = blocked._tool_func(action="create", name=f"x{bad}", system_prompt="p", tools=bad)
        assert "powerful" in out.lower()
    assert f.list_specialists().get("xshell") is None

    # allow_powerful=True on both: the powerful tool is actually granted.
    f2 = _factory(tmp_path, allow_powerful=True)
    allowed = create_manage_specialists_tool(f2, allow_powerful=True)
    allowed._tool_func(action="create", name="sh2", system_prompt="p", tools="shell")
    assert strands_tools.shell in f2._dynamic["sh2"]["tools"]


def test_load_path_enforces_powerful_gate(tmp_path):
    """Review fix (HIGH): a persisted/crafted specialist with a powerful tool must
    NOT load that tool when allow_powerful is off — the gate is at resolution, so
    config drift or a hand-written JSON can't smuggle shell/python_repl in."""
    import strands_tools

    d = tmp_path / "specialists"
    d.mkdir()
    (d / "evil.json").write_text(
        json.dumps({"name": "evil", "system_prompt": "x",
                    "tools": ["shell", "python_repl", "file_read"]}),
        encoding="utf-8",
    )
    # allow_powerful=False → shell + python_repl dropped on load; file_read kept.
    f = _factory(tmp_path, allow_powerful=False)
    tools = f._dynamic["evil"]["tools"]
    assert strands_tools.shell not in tools and strands_tools.python_repl not in tools
    assert strands_tools.file_read in tools

    # allow_powerful=True → the powerful tools load (the user opted in).
    f2 = _factory(tmp_path, allow_powerful=True)
    assert strands_tools.shell in f2._dynamic["evil"]["tools"]


def test_manage_specialists_remove(tmp_path):
    from aethon.tools.specialist_tool import create_manage_specialists_tool

    f = _factory(tmp_path)
    tool = create_manage_specialists_tool(f)
    tool._tool_func(action="create", name="tmp", system_prompt="p", tools="think")
    assert "removed" in tool._tool_func(action="remove", name="tmp").lower()
    assert "tmp" not in f.list_specialists()


# --- ask_specialist dispatcher ---


def test_ask_specialist_dispatches_to_custom():
    from aethon.tools import delegate

    class _Spec:
        def __call__(self, task):
            return "özel uzmanın sonucu"

    class _Factory:
        def get(self, name):
            assert name == "dbexpert"
            return _Spec()

        def list_specialists(self):
            return {"dbexpert": "custom"}

    delegate.set_specialist_factory(_Factory())
    try:
        out = delegate.ask_specialist._tool_func(specialist_name="dbexpert", task="x")
        assert "özel uzmanın sonucu" in out
    finally:
        delegate.set_specialist_factory(None)


def test_ask_specialist_unknown_returns_error():
    from aethon.tools import delegate

    class _Factory:
        def get(self, name):
            raise ValueError("Unknown specialist")

        def list_specialists(self):
            return {"coder": "built-in"}

    delegate.set_specialist_factory(_Factory())
    try:
        out = delegate.ask_specialist._tool_func(specialist_name="ghost", task="x")
        assert "unknown specialist" in out.lower() and "coder" in out
    finally:
        delegate.set_specialist_factory(None)


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
