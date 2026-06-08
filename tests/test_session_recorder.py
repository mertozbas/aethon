"""Tests for session recording (recorder core + hook provider + wiring)."""

from pathlib import Path

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig,
    SessionRecorderConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.hooks.session_recorder import SessionRecorderHookProvider
from aethon.agent.replay import LoadedSession


def _runtime(tmp_path, session_recorder=None):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "SOUL.md").write_text("x")
    kwargs = dict(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(tmp_path / "s"),
            logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"),
            credentials=str(tmp_path / "c"),
            recordings=str(tmp_path / "rec"),
        ),
    )
    if session_recorder is not None:
        kwargs["session_recorder"] = session_recorder
    return AethonRuntime(AethonConfig(**kwargs))


class _ToolEv:
    def __init__(self, name, inp, result=None, agent=None):
        self.tool_use = {"name": name, "input": inp, "toolUseId": "t1"}
        self.result = result
        self.agent = agent


class _InvEv:
    def __init__(self, agent):
        self.agent = agent


class _FakeAgent:
    messages = [
        {"role": "user", "content": [{"text": "hello"}]},
        {"role": "assistant", "content": [{"text": "hi there"}]},
    ]
    tool_names = ["scraper"]
    system_prompt = "SP"


def test_config_defaults():
    cfg = AethonConfig()
    assert cfg.session_recorder.enabled is False
    assert cfg.paths.recordings.endswith("recordings")


def test_not_active_by_default(tmp_path):
    rt = _runtime(tmp_path)
    assert rt._session_recorder_hook is None
    names = {h.__class__.__name__ for h in rt._get_hooks()}
    assert "SessionRecorderHookProvider" not in names


def test_active_when_enabled(tmp_path):
    rt = _runtime(tmp_path, session_recorder=SessionRecorderConfig(enabled=True))
    assert rt._session_recorder_hook is not None
    names = {h.__class__.__name__ for h in rt._get_hooks()}
    assert "SessionRecorderHookProvider" in names


def test_shared_instance_across_agents(tmp_path):
    rt = _runtime(tmp_path, session_recorder=SessionRecorderConfig(enabled=True))
    hooks1 = rt._get_hooks()
    hooks2 = rt._get_hooks()
    rec1 = next(h for h in hooks1 if h.__class__.__name__ == "SessionRecorderHookProvider")
    rec2 = next(h for h in hooks2 if h.__class__.__name__ == "SessionRecorderHookProvider")
    assert rec1 is rec2  # same recorder for the whole gateway session


def test_record_export_replay_roundtrip(tmp_path):
    rec_dir = tmp_path / "rec"
    provider = SessionRecorderHookProvider(
        config=SessionRecorderConfig(enabled=True), recordings_dir=str(rec_dir)
    )
    provider.start_recording(session_id="unit-sess")

    agent = _FakeAgent()
    provider._on_before_tool(_ToolEv("scraper", {"url": "https://x"}, agent=agent))
    provider._on_after_tool(_ToolEv("scraper", {"url": "https://x"}, result={"status": "success"}))
    provider._on_after_model(_ToolEv("", {}, agent=agent))
    provider._on_after_invocation(_InvEv(agent))

    export_path = provider.stop_and_export()
    assert export_path and Path(export_path).exists()

    ls = LoadedSession(export_path)
    assert ls.session_id == "unit-sess"
    assert len(ls.get_events_by_layer("tool")) == 2
    assert len(ls.snapshots) == 1
    snap = ls.get_snapshot(1)
    assert snap is not None
    # last exchange extracted from agent messages
    assert snap.last_query == "hello" and snap.last_result == "hi there"
    res = ls.resume_from_snapshot(1)
    assert res["status"] == "success"


def test_callbacks_never_raise_before_recording(tmp_path):
    """Event callbacks are no-ops (and don't raise) before start_recording."""
    provider = SessionRecorderHookProvider(config=SessionRecorderConfig(enabled=True))
    provider._on_before_tool(_ToolEv("x", {}))
    provider._on_after_tool(_ToolEv("x", {}, result={}))
    provider._on_after_invocation(_InvEv(_FakeAgent()))
    assert provider.stop_and_export() is None  # nothing was recording
