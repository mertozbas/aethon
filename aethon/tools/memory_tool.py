"""Memory management tool for Strands Agent.

Factory pattern: create_memory_tool(memory) returns a @tool function
that has access to VectorMemory via closure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands import tool

if TYPE_CHECKING:
    from aethon.memory.vector import VectorMemory


def create_memory_tool(memory: VectorMemory):
    """Create a manage_memory tool bound to the given VectorMemory instance.

    Args:
        memory: VectorMemory instance to use for storage/retrieval.

    Returns:
        A Strands @tool function.
    """

    @tool
    def manage_memory(
        action: str,
        content: str = "",
        query: str = "",
        category: str = "general",
        memory_id: int = 0,
    ) -> str:
        """Manage long-term memory. Store, search, list, or forget information.

        Args:
            action: "store", "search", "list", or "forget"
            content: Content to store (for store)
            query: Query to search for (for search)
            category: Category (for store/search, default: "general")
            memory_id: ID of the memory to delete (for forget)
        """
        if action == "store":
            if not content:
                return "Error: 'content' parameter is required."
            mid = memory.store(content, category)
            return f"Saved to memory (id: {mid}, category: {category})."

        elif action == "search":
            if not query:
                return "Error: 'query' parameter is required."
            results = memory.search(
                query, top_k=5,
                category=category if category != "general" else None,
            )
            if not results:
                return "No results found."
            lines = []
            for r in results:
                lines.append(
                    f"[{r['score']:.2f}] (#{r['id']}, {r['category']}) {r['content']}"
                )
            return "\n".join(lines)

        elif action == "list":
            items = memory.list_all(limit=20)
            if not items:
                return "Memory is empty."
            lines = [
                f"#{item['id']} ({item['category']}) {item['content'][:100]}"
                for item in items
            ]
            return "\n".join(lines)

        elif action == "forget":
            if not memory_id:
                return "Error: 'memory_id' parameter is required."
            deleted = memory.forget(memory_id)
            if deleted:
                return f"Memory #{memory_id} deleted."
            return f"Memory #{memory_id} not found."

        return f"Unknown action: {action}. Supported: store, search, list, forget"

    return manage_memory
