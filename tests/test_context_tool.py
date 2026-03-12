"""Tests for update_context tool."""

import pytest

from aethon.agent.context_updater import ContextUpdater
from aethon.tools.context_tool import create_context_tool


@pytest.fixture
def context_tool(tmp_path):
    """Create context tool with temporary workspace."""
    updater = ContextUpdater(str(tmp_path))
    tool = create_context_tool(updater)
    return tool, tmp_path


def test_tool_update_action(context_tool):
    """Update action stores key-value."""
    tool, tmp_path = context_tool
    result = tool._tool_func(action="update", key="Proje", value="AETHON")
    assert "guncellendi" in result


def test_tool_get_action(context_tool):
    """Get action retrieves stored value."""
    tool, tmp_path = context_tool
    tool._tool_func(action="update", key="Proje", value="AETHON")
    result = tool._tool_func(action="get", key="Proje")
    assert "AETHON" in result


def test_tool_list_action(context_tool):
    """List action returns keys."""
    tool, tmp_path = context_tool
    tool._tool_func(action="update", key="A", value="1")
    tool._tool_func(action="update", key="B", value="2")
    result = tool._tool_func(action="list")
    assert "A" in result
    assert "B" in result


def test_tool_update_missing_params(context_tool):
    """Update without key/value returns error."""
    tool, _ = context_tool
    result = tool._tool_func(action="update", key="", value="test")
    assert "Hata" in result


def test_tool_get_missing_key(context_tool):
    """Get without key returns error."""
    tool, _ = context_tool
    result = tool._tool_func(action="get", key="")
    assert "Hata" in result


def test_tool_get_nonexistent_key(context_tool):
    """Get with nonexistent key returns message."""
    tool, _ = context_tool
    result = tool._tool_func(action="get", key="Yok")
    assert "bulunamadi" in result


def test_tool_list_empty(context_tool):
    """List on empty context returns message."""
    tool, _ = context_tool
    result = tool._tool_func(action="list")
    assert "tanimlanmamis" in result


def test_tool_unknown_action(context_tool):
    """Unknown action returns error message."""
    tool, _ = context_tool
    result = tool._tool_func(action="delete")
    assert "Bilinmeyen" in result
