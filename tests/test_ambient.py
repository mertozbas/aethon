"""Tests for ambient / autonomous mode."""

import asyncio

import pytest

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig, AmbientConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.ambient import AmbientModeManager
from aethon.tools.ambient import create_ambient_tools


def _runtime(tmp_path, ambient=None):
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
        ),
    )
    if ambient is not None:
        kwargs["ambient"] = ambient
    return AethonRuntime(AethonConfig(**kwargs))


class _FakeRuntime:
    def __init__(self, reply="work done [AMBIENT_DONE]"):
        self.reply = reply
        self.calls = 0

    async def process(self, message, session_id):
        self.calls += 1
        return self.reply


def _mgr(ambient_cfg, runtime=None):
    cfg = AethonConfig(ambient=ambient_cfg)
    return AmbientModeManager(runtime or _FakeRuntime(), cfg)


# ---- config / dormancy ----

def test_ambient_config_defaults():
    cfg = AethonConfig().ambient
    assert cfg.enabled is False and cfg.auto_start is False


def test_dormant_when_disabled(tmp_path):
    rt = _runtime(tmp_path)  # ambient disabled by default
    assert rt._ambient_manager is None
    names = {getattr(t, "tool_name", getattr(t, "name", "?")) for t in rt._get_tools()}
    assert "start_ambient_mode" not in names


def test_no_tools_until_manager_wired(tmp_path):
    rt = _runtime(tmp_path, ambient=AmbientConfig(enabled=True))
    # enabled but the gateway hasn't wired a manager yet -> still no tools
    names = {getattr(t, "tool_name", getattr(t, "name", "?")) for t in rt._get_tools()}
    assert "start_ambient_mode" not in names
    # once wired, the tools appear
    rt._ambient_manager = _mgr(AmbientConfig(enabled=True))
    names = {getattr(t, "tool_name", getattr(t, "name", "?")) for t in rt._get_tools()}
    assert {"start_ambient_mode", "stop_ambient_mode", "get_ambient_status"} <= names


# ---- pure logic ----

def test_record_interaction_resets_iterations():
    m = _mgr(AmbientConfig(enabled=True))
    m.ambient_iterations = 5
    m.record_interaction("q", "r")
    assert m.last_query == "q" and m.last_response == "r"
    assert m.ambient_iterations == 0  # non-autonomous -> reset


def test_completion_signal_detection():
    m = _mgr(AmbientConfig(enabled=True, completion_signal="[DONE]"))
    assert m._check_completion_signal("all good [DONE]") is True
    assert m._check_completion_signal("still working") is False


def test_prompt_includes_signal_and_rotates():
    m = _mgr(AmbientConfig(enabled=True, completion_signal="[X]"))
    p0 = m._build_ambient_prompt()
    m.ambient_iterations = 1
    p1 = m._build_ambient_prompt()
    assert "[X]" in p0 and "[X]" in p1
    assert p0 != p1  # rotates


def test_status_shape():
    m = _mgr(AmbientConfig(enabled=True))
    s = m.status()
    assert set(s) >= {"running", "autonomous", "iterations", "pending_results"}


def test_tools_delegate_to_manager():
    m = _mgr(AmbientConfig(enabled=True))
    tools = create_ambient_tools(m)
    by = {t.tool_name: t for t in tools}
    # not running + no loop bound -> graceful messages
    assert "not running" in by["stop_ambient_mode"]().lower()
    import json
    assert json.loads(by["get_ambient_status"]())["running"] is False


# ---- async loop ----

@pytest.mark.asyncio
async def test_loop_runs_then_completes():
    fake = _FakeRuntime(reply="did work [AMBIENT_DONE]")
    m = _mgr(
        AmbientConfig(enabled=True, autonomous_cooldown_seconds=0, completion_signal="[AMBIENT_DONE]"),
        runtime=fake,
    )
    await m.start(autonomous=True)
    for _ in range(100):
        if not m.running:
            break
        await asyncio.sleep(0.01)
    assert m.running is False
    assert m.ambient_iterations >= 1
    assert fake.calls >= 1
    assert m.ambient_results_history


@pytest.mark.asyncio
async def test_stop_cancels_loop():
    # never-completing reply + zero cooldown; stop() must halt it
    fake = _FakeRuntime(reply="still working...")
    m = _mgr(
        AmbientConfig(enabled=True, autonomous_cooldown_seconds=0, autonomous_max_iterations=100000),
        runtime=fake,
    )
    await m.start(autonomous=True)
    await asyncio.sleep(0.02)
    await m.stop()
    assert m.running is False
    assert m._task is None
