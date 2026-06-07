"""Tests for the LSP tool + diagnostics hook wiring."""

from pathlib import Path

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig, LSPConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.hooks.lsp import LSPDiagnosticsHookProvider


def _runtime(tmp_path, lsp=None):
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
    if lsp is not None:
        kwargs["lsp"] = lsp
    return AethonRuntime(AethonConfig(**kwargs))


def _tool_names(runtime):
    return {getattr(t, "tool_name", getattr(t, "name", "?")) for t in runtime._get_tools()}


def _hook_names(runtime):
    return {h.__class__.__name__ for h in runtime._get_hooks()}


def test_lsp_config_defaults():
    cfg = AethonConfig().lsp
    assert cfg.enabled is False
    assert cfg.auto_diagnostics is False


def test_lsp_tool_not_registered_by_default(tmp_path):
    assert "lsp" not in _tool_names(_runtime(tmp_path))


def test_lsp_tool_registered_when_enabled(tmp_path):
    assert "lsp" in _tool_names(_runtime(tmp_path, lsp=LSPConfig(enabled=True)))


def test_lsp_hook_only_with_auto_diagnostics(tmp_path):
    # enabled but no auto_diagnostics -> no hook
    rt = _runtime(tmp_path, lsp=LSPConfig(enabled=True, auto_diagnostics=False))
    assert "LSPDiagnosticsHookProvider" not in _hook_names(rt)
    # enabled + auto_diagnostics -> hook present
    rt2 = _runtime(tmp_path, lsp=LSPConfig(enabled=True, auto_diagnostics=True))
    assert "LSPDiagnosticsHookProvider" in _hook_names(rt2)


def test_lsp_tool_status_no_crash(tmp_path):
    from aethon.tools.lsp_tool import lsp

    result = lsp(action="status")
    assert isinstance(result, dict)
    assert result.get("status") == "success"


def test_hook_extract_file_paths(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("x = 1\n")
    paths = LSPDiagnosticsHookProvider._extract_file_paths(
        {"name": "file_write", "input": {"path": str(f)}}
    )
    assert str(f) in paths


def test_hook_noop_without_servers(tmp_path):
    """With no language servers running, the hook leaves the result untouched."""
    f = tmp_path / "mod.py"
    f.write_text("x = 1\n")
    provider = LSPDiagnosticsHookProvider(config=LSPConfig(enabled=True))

    class Ev:
        tool_use = {"name": "file_write", "input": {"path": str(f)}}
        result = {"content": [{"text": "ok"}]}

    ev = Ev()
    provider._on_tool_complete(ev)  # must not raise
    assert ev.result["content"] == [{"text": "ok"}]


def test_hook_within_home():
    provider = LSPDiagnosticsHookProvider()
    assert provider._within_home(str(Path.home() / "x.py")) is True
    assert provider._within_home("/etc/passwd") is False
