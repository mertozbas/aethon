"""Tests for MCP server integration."""

import pytest
from unittest.mock import MagicMock, patch

from aethon.tools.mcp_integration import MCPToolLoader


def test_mcp_loader_creation():
    """MCPToolLoader can be created with configs."""
    configs = [{"command": "echo", "args": ["hello"]}]
    loader = MCPToolLoader(configs)
    assert loader.server_configs == configs
    assert loader._clients == []
    assert loader._tools == []


def test_mcp_loader_empty_configs():
    """MCPToolLoader handles empty config list."""
    loader = MCPToolLoader([])
    tools = loader.start()
    assert tools == []
    assert loader.get_tools() == []


def test_mcp_loader_skips_missing_command():
    """MCPToolLoader skips configs without command."""
    loader = MCPToolLoader([{"args": ["test"]}])
    tools = loader.start()
    assert tools == []


@patch("aethon.tools.mcp_integration.MCPClient")
@patch("aethon.tools.mcp_integration.stdio_client")
@patch("aethon.tools.mcp_integration.StdioServerParameters")
def test_mcp_loader_starts_server(mock_params, mock_stdio, mock_mcp_class):
    """MCPToolLoader starts MCP servers and loads tools."""
    mock_tool = MagicMock()
    mock_client = MagicMock()
    mock_client.list_tools_sync.return_value = [mock_tool]
    mock_mcp_class.return_value = mock_client

    loader = MCPToolLoader([{"command": "test-server", "args": ["--flag"]}])
    tools = loader.start()

    assert len(tools) == 1
    assert tools[0] == mock_tool
    mock_client.start.assert_called_once()
    mock_client.list_tools_sync.assert_called_once()


@patch("aethon.tools.mcp_integration.MCPClient")
@patch("aethon.tools.mcp_integration.stdio_client")
@patch("aethon.tools.mcp_integration.StdioServerParameters")
def test_mcp_loader_stop(mock_params, mock_stdio, mock_mcp_class):
    """MCPToolLoader stops all clients."""
    mock_client = MagicMock()
    mock_client.list_tools_sync.return_value = []
    mock_mcp_class.return_value = mock_client

    loader = MCPToolLoader([{"command": "test-server"}])
    loader.start()
    assert len(loader._clients) == 1

    loader.stop()
    mock_client.stop.assert_called_once()
    assert loader._clients == []
    assert loader._tools == []


@patch("aethon.tools.mcp_integration.MCPClient")
@patch("aethon.tools.mcp_integration.stdio_client")
@patch("aethon.tools.mcp_integration.StdioServerParameters")
def test_mcp_loader_handles_error(mock_params, mock_stdio, mock_mcp_class):
    """MCPToolLoader handles server start errors gracefully."""
    mock_mcp_class.side_effect = RuntimeError("Connection failed")

    loader = MCPToolLoader([{"command": "broken-server"}])
    tools = loader.start()
    assert tools == []
    assert loader._clients == []


@patch("aethon.tools.mcp_integration.MCPClient")
@patch("aethon.tools.mcp_integration.stdio_client")
@patch("aethon.tools.mcp_integration.StdioServerParameters")
def test_mcp_loader_multiple_servers(mock_params, mock_stdio, mock_mcp_class):
    """MCPToolLoader loads tools from multiple servers."""
    tool1, tool2 = MagicMock(), MagicMock()

    mock_client1 = MagicMock()
    mock_client1.list_tools_sync.return_value = [tool1]
    mock_client2 = MagicMock()
    mock_client2.list_tools_sync.return_value = [tool2]
    mock_mcp_class.side_effect = [mock_client1, mock_client2]

    loader = MCPToolLoader([
        {"command": "server1"},
        {"command": "server2"},
    ])
    tools = loader.start()
    assert len(tools) == 2
    assert len(loader._clients) == 2
