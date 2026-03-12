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
        """Uzun vadeli hafizayi yonet. Bilgi kaydet, ara, listele veya unut.

        Args:
            action: "store" (kaydet), "search" (ara), "list" (listele), "forget" (unut)
            content: Kaydedilecek icerik (store icin)
            query: Aranacak sorgu (search icin)
            category: Kategori (store/search icin, varsayilan: "general")
            memory_id: Silinecek hafiza ID (forget icin)
        """
        if action == "store":
            if not content:
                return "Hata: 'content' parametresi gerekli."
            mid = memory.store(content, category)
            return f"Hafizaya kaydedildi (id: {mid}, kategori: {category})."

        elif action == "search":
            if not query:
                return "Hata: 'query' parametresi gerekli."
            results = memory.search(
                query, top_k=5,
                category=category if category != "general" else None,
            )
            if not results:
                return "Sonuc bulunamadi."
            lines = []
            for r in results:
                lines.append(
                    f"[{r['score']:.2f}] (#{r['id']}, {r['category']}) {r['content']}"
                )
            return "\n".join(lines)

        elif action == "list":
            items = memory.list_all(limit=20)
            if not items:
                return "Hafiza bos."
            lines = [
                f"#{item['id']} ({item['category']}) {item['content'][:100]}"
                for item in items
            ]
            return "\n".join(lines)

        elif action == "forget":
            if not memory_id:
                return "Hata: 'memory_id' parametresi gerekli."
            deleted = memory.forget(memory_id)
            if deleted:
                return f"Hafiza #{memory_id} silindi."
            return f"Hafiza #{memory_id} bulunamadi."

        return f"Bilinmeyen action: {action}. Desteklenen: store, search, list, forget"

    return manage_memory
