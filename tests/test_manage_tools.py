"""Tests for manage_tools (dynamic tool loading) gating."""

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig,
    RuntimeToolsConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.hooks.security import SecurityHookProvider
from aethon.agent.hooks.approval import ApprovalHookProvider
from aethon.tools.manage_tools import manage_tools


def _runtime(tmp_path, runtime_tools=None):
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
    if runtime_tools is not None:
        kwargs["runtime_tools"] = runtime_tools
    return AethonRuntime(AethonConfig(**kwargs))


def _tool_names(runtime):
    return {getattr(t, "tool_name", getattr(t, "name", "?")) for t in runtime._get_tools()}


class _Ev:
    def __init__(self, name, inp):
        self.tool_use = {"name": name, "input": inp}
        self.cancel_tool = None


class _IEv(_Ev):
    def __init__(self, name, inp):
        super().__init__(name, inp)
        self.interrupted = False

    def interrupt(self, **kwargs):
        self.interrupted = True


class _FakeAgent:
    def __init__(self, cfg):
        self.__aethon_config__ = cfg


def test_runtime_tools_config_defaults():
    cfg = AethonConfig().runtime_tools
    assert cfg.enabled is False
    assert cfg.allow_create is False
    assert cfg.allow_install is False


def test_approval_default_includes_manage_tools():
    assert "manage_tools" in AethonConfig().approval.requires_approval


def test_not_registered_by_default(tmp_path):
    assert "manage_tools" not in _tool_names(_runtime(tmp_path))


def test_registered_when_enabled(tmp_path):
    rt = _runtime(tmp_path, runtime_tools=RuntimeToolsConfig(enabled=True))
    assert "manage_tools" in _tool_names(rt)


def test_agent_config_injected(tmp_path):
    rt = _runtime(tmp_path, runtime_tools=RuntimeToolsConfig(enabled=True))
    agent = rt.get_or_create_agent("s1")
    assert getattr(agent, "__aethon_config__", None) is rt.config


def test_security_blocks_create_without_allow():
    sec = SecurityHookProvider(
        workspace="/tmp", runtime_tools=RuntimeToolsConfig(enabled=True, allow_create=False)
    )
    ev = _Ev("manage_tools", {"action": "create", "code": "x"})
    sec.check_tool_safety(ev)
    assert ev.cancel_tool is not None and "allow_create" in ev.cancel_tool


def test_security_blocks_add_without_allow():
    sec = SecurityHookProvider(
        workspace="/tmp", runtime_tools=RuntimeToolsConfig(enabled=True, allow_install=False)
    )
    ev = _Ev("manage_tools", {"action": "add", "tools": "x"})
    sec.check_tool_safety(ev)
    assert ev.cancel_tool is not None and "allow_install" in ev.cancel_tool


def test_security_allows_list_and_create_when_permitted():
    sec = SecurityHookProvider(
        workspace="/tmp",
        runtime_tools=RuntimeToolsConfig(enabled=True, allow_create=True, allow_install=True),
    )
    for action in ("list", "discover", "sandbox", "create", "add"):
        ev = _Ev("manage_tools", {"action": action})
        sec.check_tool_safety(ev)
        assert ev.cancel_tool is None, action


def test_security_normalizes_case():
    sec = SecurityHookProvider(
        workspace="/tmp", runtime_tools=RuntimeToolsConfig(enabled=True, allow_create=False)
    )
    ev = _Ev("manage_tools", {"action": "  CREATE "})
    sec.check_tool_safety(ev)
    assert ev.cancel_tool is not None


def test_approval_action_aware():
    ap = ApprovalHookProvider(["manage_tools"])
    # dangerous -> interrupt
    ev = _IEv("manage_tools", {"action": "create"})
    ap.check_approval(ev)
    assert ev.interrupted is True
    # read-only -> auto-approve
    ev2 = _IEv("manage_tools", {"action": "list"})
    ap.check_approval(ev2)
    assert ev2.interrupted is False


def test_in_tool_check_blocks_when_disabled():
    cfg = AethonConfig(runtime_tools=RuntimeToolsConfig(enabled=False))
    r = manage_tools(action="create", code="from strands import tool", agent=_FakeAgent(cfg))
    assert r["status"] == "error" and "enabled=false" in r["content"][0]["text"]


def test_in_tool_check_blocks_create_without_allow():
    cfg = AethonConfig(runtime_tools=RuntimeToolsConfig(enabled=True, allow_create=False))
    r = manage_tools(action="create", code="from strands import tool", agent=_FakeAgent(cfg))
    assert r["status"] == "error" and "allow_create" in r["content"][0]["text"]
