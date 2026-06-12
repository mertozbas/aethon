"""Tests for ApprovalHookProvider."""

import pytest

from strands import Agent
from aethon.agent.fake_model import EchoModel
from strands.hooks import HookRegistry
from strands.hooks.events import BeforeToolCallEvent
from strands.interrupt import InterruptException

from aethon.agent.hooks.approval import ApprovalHookProvider


@pytest.fixture
def approval_hook():
    return ApprovalHookProvider()


@pytest.fixture
def custom_hook():
    return ApprovalHookProvider(requires_approval=["http_request", "send_message"])


@pytest.fixture
def agent():
    model = EchoModel()
    return Agent(model=model, system_prompt="Test agent")


def _make_event(agent, tool_name: str, tool_input: dict = None):
    """Create a BeforeToolCallEvent for testing."""
    event = BeforeToolCallEvent(
        agent=agent,
        selected_tool=None,
        tool_use={
            "name": tool_name,
            "toolUseId": "test-001",
            "input": tool_input or {},
        },
        invocation_state={},
    )
    return event


def test_approval_hook_creation(approval_hook):
    """ApprovalHookProvider creates with default requires_approval."""
    assert "shell" in approval_hook.requires_approval
    assert "file_write" in approval_hook.requires_approval


def test_custom_requires_approval(custom_hook):
    """Custom requires_approval list works."""
    assert "http_request" in custom_hook.requires_approval
    assert "send_message" in custom_hook.requires_approval
    assert "shell" not in custom_hook.requires_approval


def test_register_hooks(approval_hook):
    """Hook registers with HookRegistry."""
    registry = HookRegistry()
    approval_hook.register_hooks(registry)
    # Should not raise


def test_shell_triggers_interrupt(agent, approval_hook):
    """Shell tool triggers InterruptException."""
    event = _make_event(agent, "shell", {"command": "ls"})
    with pytest.raises(InterruptException):
        approval_hook.check_approval(event)


def test_file_write_triggers_interrupt(agent, approval_hook):
    """file_write tool triggers InterruptException."""
    event = _make_event(agent, "file_write", {"path": "/tmp/test.txt"})
    with pytest.raises(InterruptException):
        approval_hook.check_approval(event)


def test_safe_tool_no_interrupt(agent, approval_hook):
    """Safe tools (think, file_read) do not trigger interrupt."""
    event = _make_event(agent, "think", {"thought": "test"})
    # Should not raise
    approval_hook.check_approval(event)


def test_file_read_no_interrupt(agent, approval_hook):
    """file_read is safe — no interrupt."""
    event = _make_event(agent, "file_read", {"path": "/tmp/test.txt"})
    approval_hook.check_approval(event)


def test_custom_hook_triggers_on_custom_tools(agent, custom_hook):
    """Custom hook triggers on custom tool list."""
    event = _make_event(agent, "http_request", {"url": "https://example.com"})
    with pytest.raises(InterruptException):
        custom_hook.check_approval(event)


def test_custom_hook_ignores_default_tools(agent, custom_hook):
    """Custom hook ignores default tools not in its list."""
    event = _make_event(agent, "shell", {"command": "ls"})
    # shell is not in custom_hook's requires_approval — should not raise
    custom_hook.check_approval(event)


# --- S6: the resume decision is enforced (the F6 half-wiring fix) ------------


def _seed_response(agent, event, tool_name, response):
    """Pre-seed the interrupt response so the second check_approval RETURNS it
    (simulating a resume) instead of raising."""
    from strands.interrupt import Interrupt

    name = f"{tool_name}_approval"
    iid = event._interrupt_id(name)
    agent._interrupt_state.interrupts[iid] = Interrupt(iid, name, None, response)


def test_resume_denied_cancels_tool(agent, approval_hook):
    """On resume with approved=False, the tool is cancelled with the reason."""
    event = _make_event(agent, "shell", {"command": "rm -rf x"})
    _seed_response(agent, event, "shell", {"approved": False, "reason": "kullanıcı reddetti."})
    approval_hook.check_approval(event)  # must NOT raise — it resumes
    assert event.cancel_tool  # truthy
    assert "reddetti" in str(event.cancel_tool)


def test_resume_approved_does_not_cancel(agent, approval_hook):
    """On resume with approved=True, the tool proceeds (no cancel)."""
    event = _make_event(agent, "shell", {"command": "ls"})
    _seed_response(agent, event, "shell", {"approved": True, "reason": ""})
    approval_hook.check_approval(event)
    assert event.cancel_tool is False


def test_resume_unanswerable_cancels_with_message(agent, approval_hook):
    """A fail-closed decision (no 'approved' key truthy) cancels with its reason."""
    event = _make_event(agent, "file_write", {"path": "/tmp/x"})
    _seed_response(
        agent, event, "file_write",
        {"approved": False, "reason": "bu kanal yanıtlayamıyor"},
    )
    approval_hook.check_approval(event)
    assert "yanıtlayamıyor" in str(event.cancel_tool)
