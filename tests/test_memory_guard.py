"""Tests for MemoryGuardHookProvider."""

import pytest
from unittest.mock import MagicMock

from aethon.agent.hooks.memory_guard import MemoryGuardHookProvider


def _make_event(tool_name="manage_memory", action="store", content=""):
    event = MagicMock()
    event.tool_use = {
        "name": tool_name,
        "input": {"action": action, "content": content},
    }
    event.cancel_tool = False
    return event


def test_memory_guard_creation():
    """MemoryGuardHookProvider can be created."""
    hook = MemoryGuardHookProvider()
    assert len(hook._compiled) == len(hook.DEFAULT_PATTERNS)


def test_guard_blocks_api_key():
    """API key pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="api_key=sk-abc123xyz")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_password():
    """Password pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="password=mysecretpass123")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_token():
    """Token pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="secret=ghp_xxxxxxxxxxxx")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_credit_card():
    """Credit card pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="Kart numaram 4111 1111 1111 1111")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_ssn():
    """SSN pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="SSN: 123-45-6789")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_private_key():
    """Private key pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(
        content="-----BEGIN RSA PRIVATE KEY-----\nMIIEpA..."
    )
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_blocks_ssh_key():
    """SSH key pattern is blocked."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="ssh-rsa AAAAB3NzaC1yc2EAAAA user@host")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_allows_normal_content():
    """Normal content passes through."""
    hook = MemoryGuardHookProvider()
    event = _make_event(content="Python 3.10 kullan, asyncio tercih et.")
    hook.guard_memory(event)
    assert event.cancel_tool is False


def test_guard_ignores_non_store_action():
    """Non-store actions pass through."""
    hook = MemoryGuardHookProvider()
    event = _make_event(action="search", content="api_key=sk-abc")
    hook.guard_memory(event)
    assert event.cancel_tool is False


def test_guard_ignores_non_memory_tool():
    """Non-memory tools pass through."""
    hook = MemoryGuardHookProvider()
    event = _make_event(tool_name="shell", content="api_key=sk-abc")
    hook.guard_memory(event)
    assert event.cancel_tool is False


def test_guard_custom_patterns():
    """Custom patterns are applied."""
    hook = MemoryGuardHookProvider(custom_patterns=[r"CUSTOM_SECRET_\w+"])
    event = _make_event(content="benim CUSTOM_SECRET_abc123 degerim")
    hook.guard_memory(event)
    assert "BLOCKED" in str(event.cancel_tool)


def test_guard_register_hooks():
    """Hook can register with registry."""
    hook = MemoryGuardHookProvider()
    registry = MagicMock()
    hook.register_hooks(registry)
    assert registry.add_callback.call_count == 1
