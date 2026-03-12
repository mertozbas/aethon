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
        """CONTEXT.md dosyasini yonet. Baglam bilgisi ekle, guncelle, oku veya listele.

        Args:
            action: Islem tipi — "update" (ekle/guncelle), "get" (oku), "list" (anahtarlari listele)
            key: Baglam anahtari (update ve get icin gerekli)
            value: Baglam degeri (update icin gerekli)
        """
        if action == "update":
            if not key or not value:
                return "Hata: 'key' ve 'value' parametreleri gerekli."
            return updater.update(key, value)
        elif action == "get":
            if not key:
                return "Hata: 'key' parametresi gerekli."
            result = updater.get(key)
            return result if result else f"Anahtar bulunamadi: {key}"
        elif action == "list":
            keys = updater.list_keys()
            return "\n".join(keys) if keys else "Hicbir anahtar tanimlanmamis."
        return f"Bilinmeyen action: {action}. Desteklenen: update, get, list"

    return update_context
