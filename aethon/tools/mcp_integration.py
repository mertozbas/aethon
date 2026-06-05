"""MCP (Model Context Protocol) server integration.

Loads tools from external MCP servers and makes them available to AETHON agents.
"""

import logging
from typing import Any

from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters, stdio_client


logger = logging.getLogger("aethon.mcp")


class MCPToolLoader:
    """Manages MCP server connections and tool loading."""

    def __init__(self, server_configs: list[dict]):
        """Initialize with server configurations.

        Each config dict should have:
            - command: str — executable to run
            - args: list[str] — command arguments (optional)
            - env: dict — environment variables (optional)
        """
        self.server_configs = server_configs
        self._clients: list = []
        self._tools: list = []

    def start(self) -> list:
        """Start all MCP servers and collect their tools.

        Returns:
            Combined list of tools from all servers.
        """
        self._tools = []
        for cfg in self.server_configs:
            command = cfg.get("command", "")
            if not command:
                logger.warning("MCP server config is missing 'command', skipping")
                continue

            args = cfg.get("args", [])
            env = cfg.get("env", None)

            try:
                params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env,
                )
                client = MCPClient(lambda: stdio_client(params))
                client.start()
                tools = client.list_tools_sync()
                self._clients.append(client)
                self._tools.extend(tools)
                logger.info(
                    f"MCP server started: {command} "
                    f"({len(tools)} tools loaded)"
                )
            except Exception as e:
                logger.warning(f"MCP server error ({command}): {e}")

        return self._tools

    def get_tools(self) -> list:
        """Get all loaded MCP tools."""
        return self._tools

    def stop(self):
        """Stop all MCP server connections."""
        for client in self._clients:
            try:
                client.stop()
            except Exception as e:
                logger.warning(f"MCP client stop error: {e}")
        self._clients.clear()
        self._tools.clear()
        logger.info("All MCP servers stopped")
