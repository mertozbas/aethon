"""Tests for InputValidatorHookProvider (Phase 8 / R16)."""

from unittest.mock import MagicMock

from aethon.agent.hooks.input_validator import InputValidatorHookProvider


def _event(tool_name, tool_input):
    event = MagicMock()
    event.tool_use = {"name": tool_name, "input": tool_input}
    event.cancel_tool = None
    return event


def test_empty_shell_command_is_cancelled():
    """The opaque 'command field required' pydantic error becomes a
    self-describing cancellation."""
    hook = InputValidatorHookProvider()
    event = _event("shell", {"command": "   "})
    hook.validate_input(event)
    assert event.cancel_tool
    assert "command" in event.cancel_tool


def test_missing_shell_command_is_cancelled():
    hook = InputValidatorHookProvider()
    event = _event("shell", {})
    hook.validate_input(event)
    assert event.cancel_tool


def test_valid_shell_command_passes():
    hook = InputValidatorHookProvider()
    event = _event("shell", {"command": "ls -la"})
    hook.validate_input(event)
    assert not event.cancel_tool


def test_file_write_without_path_is_cancelled():
    hook = InputValidatorHookProvider()
    event = _event("file_write", {"content": "x"})
    hook.validate_input(event)
    assert event.cancel_tool
    assert "path" in event.cancel_tool


def test_file_tools_accept_alternative_path_keys():
    hook = InputValidatorHookProvider()
    event = _event("file_read", {"file_path": "/tmp/x"})
    hook.validate_input(event)
    assert not event.cancel_tool


def test_send_message_requires_channel_and_text():
    hook = InputValidatorHookProvider()
    event = _event("send_message", {"channel": "telegram", "text": ""})
    hook.validate_input(event)
    assert event.cancel_tool
    assert "text" in event.cancel_tool


def test_unknown_tools_are_ignored():
    hook = InputValidatorHookProvider()
    event = _event("think", {})
    hook.validate_input(event)
    assert not event.cancel_tool
