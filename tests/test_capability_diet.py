"""Tests for the capability diet (Phase 10 C6)."""

import aethon.agent.capability_diet as cd
from aethon.agent.capability_diet import DISCOVERABLE_TOOLS, select_tools


class _T:
    def __init__(self, name):
        self.tool_name = name


def _names(tools):
    return [t.tool_name for t in tools]


def test_core_tools_always_kept():
    tools = [_T("file_read"), _T("shell"), _T("manage_tasks")]
    # Nothing is discoverable → the diet keeps everything regardless of hint.
    assert select_tools(tools, "bir şeyler yap") == tools


def test_discoverable_kept_only_on_keyword():
    tools = [_T("file_read"), _T("use_mac"), _T("use_github")]
    out = _names(select_tools(tools, "takvimime yarına bir etkinlik ekle"))
    assert "use_mac" in out          # calendar/takvim keyword pulls it in
    assert "use_github" not in out   # no github keyword → pruned
    assert "file_read" in out        # core always


def test_discoverable_dropped_without_keyword():
    tools = [_T("file_read"), _T("use_mac")]
    out = _names(select_tools(tools, "bu Python kodunu refactor et ve testleri çalıştır"))
    assert "use_mac" not in out
    assert "file_read" in out


def test_empty_hint_prunes_nothing():
    tools = [_T("file_read"), _T("use_mac")]
    assert select_tools(tools, "") == tools
    assert select_tools(tools, "   ") == tools


def test_github_and_computer_keywords():
    tools = [_T("use_github"), _T("use_computer"), _T("file_read")]
    out = _names(select_tools(tools, "open a pull request on the repo"))
    assert "use_github" in out and "use_computer" not in out

    out = _names(select_tools(tools, "take a screenshot of the screen"))
    assert "use_computer" in out and "use_github" not in out


def test_every_discoverable_has_triggers():
    for name, triggers in DISCOVERABLE_TOOLS.items():
        assert isinstance(triggers, tuple) and len(triggers) >= 1


def _runtime(tmp_path, capability_diet):
    from aethon.agent.runtime import AethonRuntime
    from aethon.config import AethonConfig, ModelConfig, PathsConfig

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("x")
    (ws / "TOOLS.md").write_text("x")
    config = AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        paths=PathsConfig(
            workspace=str(ws), sessions=str(tmp_path / "s"), logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"), credentials=str(tmp_path / "c"),
        ),
    )
    config.core_loop.capability_diet = capability_diet
    return AethonRuntime(config)


def test_runtime_threads_hint_when_diet_on(tmp_path, monkeypatch):
    """The building message reaches the diet at agent-build time (C6 is per
    session, decided from that message)."""
    seen = {}
    real = cd.select_tools

    def spy(tools, hint):
        seen["hint"] = hint
        return real(tools, hint)

    monkeypatch.setattr(cd, "select_tools", spy)
    runtime = _runtime(tmp_path, capability_diet=True)
    runtime.get_or_create_agent("cli:u", hint="takvime ekle")
    assert seen.get("hint") == "takvime ekle"


def test_runtime_diet_off_does_not_filter(tmp_path, monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(cd, "select_tools", lambda t, h: called.__setitem__("n", called["n"] + 1) or t)
    runtime = _runtime(tmp_path, capability_diet=False)   # default off
    runtime.get_or_create_agent("cli:u", hint="takvime ekle")
    assert called["n"] == 0   # diet not invoked when disabled
