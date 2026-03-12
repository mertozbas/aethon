"""Tests for ApprovalHookProvider."""

import pytest

from strands import Agent
from strands.models.ollama import OllamaModel
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
    model = OllamaModel(
        host="http://localhost:11434",
        model_id="qwen3-coder-next",
    )
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
