"""Tests for use_computer gating (high-risk computer automation)."""

import importlib.util

from aethon.config import (
    AethonConfig, PathsConfig, ModelConfig, MemoryConfig, MCPConfig,
    CapabilitiesConfig, ComputerCapability, ApprovalConfig,
)
from aethon.agent.runtime import AethonRuntime
from aethon.agent.hooks.approval import ApprovalHookProvider


def _runtime(tmp_path, computer=None, approval=None):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    (workspace / "SOUL.md").write_text("x")
    caps = CapabilitiesConfig()
    if computer is not None:
        caps.computer = computer
    kwargs = dict(
        model=ModelConfig(provider="fake", model_id="fake"),
        memory=MemoryConfig(enabled=False),
        mcp=MCPConfig(enabled=False),
        capabilities=caps,
        paths=PathsConfig(
            workspace=str(workspace),
            sessions=str(tmp_path / "s"),
            logs=str(tmp_path / "l"),
            memory_db=str(tmp_path / "m.sqlite"),
            credentials=str(tmp_path / "c"),
        ),
    )
    if approval is not None:
        kwargs["approval"] = approval
    return AethonRuntime(AethonConfig(**kwargs))


def _tool_names(rt):
    return {getattr(t, "tool_name", getattr(t, "name", "?")) for t in rt._get_tools()}


def _hook_names(rt):
    return {h.__class__.__name__ for h in rt._get_hooks()}


class _IEv:
    def __init__(self, name, inp):
        self.tool_use = {"name": name, "input": inp}
        self.interrupted = False

    def interrupt(self, **kwargs):
        self.interrupted = True


def test_config_defaults():
    c = AethonConfig().capabilities.computer
    assert c.enabled is False and c.require_approval is True


def test_module_imports_without_pyautogui():
    from aethon.tools.vendor.use_computer import use_computer
    assert getattr(use_computer, "tool_name", None) == "use_computer"


def test_not_registered_by_default(tmp_path):
    assert "use_computer" not in _tool_names(_runtime(tmp_path))


def test_not_registered_without_pyautogui(tmp_path):
    """Even enabled, the tool isn't advertised when pyautogui is absent."""
    rt = _runtime(tmp_path, computer=ComputerCapability(enabled=True))
    has_pyautogui = importlib.util.find_spec("pyautogui") is not None
    assert ("use_computer" in _tool_names(rt)) == has_pyautogui


def test_approval_auto_activates_for_computer(tmp_path):
    """Enabling computer with require_approval activates approval even if approval
    is globally disabled — and only for use_computer."""
    rt = _runtime(
        tmp_path,
        computer=ComputerCapability(enabled=True, require_approval=True),
        approval=ApprovalConfig(enabled=False),
    )
    hooks = rt._get_hooks()
    assert "ApprovalHookProvider" in {h.__class__.__name__ for h in hooks}
    ap = next(h for h in hooks if h.__class__.__name__ == "ApprovalHookProvider")
    assert "use_computer" in ap.requires_approval
    # global approval off -> shell/file_write are NOT gated by this hook
    assert "shell" not in ap.requires_approval


def test_no_approval_when_require_approval_false(tmp_path):
    rt = _runtime(
        tmp_path,
        computer=ComputerCapability(enabled=True, require_approval=False),
        approval=ApprovalConfig(enabled=False),
    )
    assert "ApprovalHookProvider" not in _hook_names(rt)


def test_approval_action_aware():
    ap = ApprovalHookProvider(["use_computer"], computer=ComputerCapability(enabled=True))
    for sensitive in ("type", "click", "hotkey", "drag"):
        ev = _IEv("use_computer", {"action": sensitive})
        ap.check_approval(ev)
        assert ev.interrupted is True, sensitive
    for safe in ("screenshot", "mouse_position", "screen_size", "get_system_info"):
        ev = _IEv("use_computer", {"action": safe})
        ap.check_approval(ev)
        assert ev.interrupted is False, safe
