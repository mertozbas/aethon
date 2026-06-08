"""Tests for the tool-output guard (context-overflow protection)."""

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig, PerformanceConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.hooks.output_guard import ToolOutputGuardHookProvider


class _Ev:
    def __init__(self, name, content):
        self.tool_use = {"name": name}
        self.result = {"content": content}


def test_large_output_truncated():
    g = ToolOutputGuardHookProvider(max_chars=1000)
    ev = _Ev("shell", [{"text": "x" * 50000}])
    g._cap(ev)
    out = ev.result["content"][0]["text"]
    assert len(out) < 5000
    assert "truncated" in out
    assert out.startswith("x")  # head preserved


def test_small_output_untouched():
    g = ToolOutputGuardHookProvider(max_chars=12000)
    ev = _Ev("shell", [{"text": "small output"}])
    g._cap(ev)
    assert ev.result["content"][0]["text"] == "small output"


def test_disabled_when_zero():
    g = ToolOutputGuardHookProvider(max_chars=0)
    ev = _Ev("shell", [{"text": "y" * 50000}])
    g._cap(ev)
    assert len(ev.result["content"][0]["text"]) == 50000


def test_non_dict_content_safe():
    g = ToolOutputGuardHookProvider(max_chars=10)
    ev = _Ev("shell", "not a list")
    g._cap(ev)  # must not raise


def test_config_default():
    assert AethonConfig().performance.max_tool_output_chars == 12000


def test_registered_in_runtime(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("x")
    rt = AethonRuntime(AethonConfig(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        paths=PathsConfig(
            workspace=str(ws), sessions=str(tmp_path / "s"), logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"), credentials=str(tmp_path / "c"),
        ),
    ))
    names = {h.__class__.__name__ for h in rt._get_hooks()}
    assert "ToolOutputGuardHookProvider" in names

    # disabled -> not registered
    rt.config.performance.max_tool_output_chars = 0
    names2 = {h.__class__.__name__ for h in rt._get_hooks()}
    assert "ToolOutputGuardHookProvider" not in names2
