"""Context update tool.

Provides update_context tool for agents to manage CONTEXT.md automatically.
Uses closure pattern (same as memory_tool.py).
"""

from strands import tool

from aethon.agent.context_updater import ContextUpdater


def create_context_tool(updater: ContextUpdater):
    """Create an update_context tool bound to a ContextUpdater instance."""

    @tool
    def update_context(action: str, key: str = "", value: str = "") -> str:
        """Manage the CONTEXT.md file. Add, update, read, or list context information.

        Args:
            action: Operation type — "update" (add/update), "get" (read), "list" (list keys)
            key: Context key (required for update and get)
            value: Context value (required for update)
        """
        if action == "update":
            if not key or not value:
                return "Error: 'key' and 'value' parameters are required."
            return updater.update(key, value)
        elif action == "get":
            if not key:
                return "Error: 'key' parameter is required."
            result = updater.get(key)
            return result if result else f"Key not found: {key}"
        elif action == "list":
            keys = updater.list_keys()
            return "\n".join(keys) if keys else "No keys defined."
        return f"Unknown action: {action}. Supported: update, get, list"

    return update_context
