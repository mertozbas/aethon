# AETHON — Faz 2: Kanallar + Hafiza

> Hedef: Tum mesajlasma kanallari calisiyor, kalici hafiza aktif.
> Tahmini Sure: 1-2 Hafta
> Oncelik: P1 (Onemli)
> Onkosul: Faz 1 tamamlanmis

---

## 1. Faz Ozeti

Faz 2 sonunda su kanallar calisiyor olacak:

```
┌──────────┐   ┌───────────┐   ┌──────────┐   ┌─────────┐
│ Telegram │   │  Discord  │   │  Slack   │   │WhatsApp │
│ (aiogram)│   │(discord.py)│  │(slack-bolt)│  │(neonize)│
└────┬─────┘   └─────┬─────┘   └─────┬────┘   └────┬────┘
     │               │               │              │
     └───────────────┴───────┬───────┴──────────────┘
                             │
                      MessageRouter
                             │
                      AethonRuntime
                             │
                    ┌────────┴────────┐
                    │                 │
              VectorMemory    SessionManager
              (SQLite+Embed)  (FileSession)
```

---

## 2. Implementasyon Sirasi

### Adim 2.1: TelegramAdapter

**Dosya:** `aethon/channels/telegram.py`
**Kutuphane:** `aiogram>=3.0.0` (asyncio-native)

```python
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

class TelegramAdapter(ChannelAdapter):
    """Telegram Bot API adapter (aiogram 3.x)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.token = config.channels.telegram.token
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None

    async def start(self) -> None:
        if not self.token:
            raise ValueError("Telegram token gerekli (config.channels.telegram.token)")

        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()

        @self.dp.message()
        async def handle_message(tg_msg: types.Message):
            # Text mesaji
            if tg_msg.text:
                inbound = InboundMessage(
                    channel="telegram",
                    sender_id=str(tg_msg.from_user.id),
                    sender_name=tg_msg.from_user.full_name or "Unknown",
                    text=tg_msg.text,
                    reply_to=str(tg_msg.reply_to_message.message_id) if tg_msg.reply_to_message else None,
                    timestamp=tg_msg.date,
                    raw={"message_id": tg_msg.message_id, "chat_id": tg_msg.chat.id},
                )
                await self.on_message(inbound)

        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        if self.dp:
            await self.dp.stop_polling()
        if self.bot:
            await self.bot.session.close()

    async def send(self, message: OutboundMessage) -> None:
        if self.bot:
            chat_id = message.raw.get("chat_id") if hasattr(message, "raw") else int(message.recipient_id)
            await self.bot.send_message(
                chat_id=chat_id,
                text=message.text,
                parse_mode=ParseMode.MARKDOWN,
            )
```

**Kurulum:**
1. BotFather'dan bot olustur → token al
2. `config.yaml`'a ekle:
   ```yaml
   channels:
     telegram:
       enabled: true
       token: "${TELEGRAM_BOT_TOKEN}"
   ```
3. `~/.aethon/credentials/telegram.env`'e yaz: `TELEGRAM_BOT_TOKEN=123456:ABC...`

---

### Adim 2.2: DiscordAdapter

**Dosya:** `aethon/channels/discord_adapter.py`
**Kutuphane:** `discord.py>=2.0.0`

```python
import discord
from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

class DiscordAdapter(ChannelAdapter):
    """Discord Bot adapter (discord.py 2.x)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.token = config.channels.discord.token

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_message(msg: discord.Message):
            # Bot'un kendi mesajlarini yoksay
            if msg.author == self.client.user:
                return

            # Sadece DM veya mention
            is_dm = isinstance(msg.channel, discord.DMChannel)
            is_mentioned = self.client.user in msg.mentions if self.client.user else False

            if not (is_dm or is_mentioned):
                return

            text = msg.content
            # Mention'i kaldir
            if self.client.user:
                text = text.replace(f"<@{self.client.user.id}>", "").strip()

            inbound = InboundMessage(
                channel="discord",
                sender_id=str(msg.author.id),
                sender_name=msg.author.display_name,
                text=text,
                thread_id=str(msg.channel.id) if hasattr(msg.channel, 'id') else None,
                raw={"channel_id": msg.channel.id, "message_id": msg.id},
            )
            await self.on_message(inbound)

    async def start(self) -> None:
        if not self.token:
            raise ValueError("Discord token gerekli")
        await self.client.start(self.token)

    async def stop(self) -> None:
        await self.client.close()

    async def send(self, message: OutboundMessage) -> None:
        channel_id = message.raw.get("channel_id") if hasattr(message, "raw") else int(message.recipient_id)
        channel = self.client.get_channel(channel_id)
        if channel:
            await channel.send(message.text)
```

**Kurulum:**
1. Discord Developer Portal'dan bot olustur → token al
2. Bot'a `MESSAGE_CONTENT` intent izni ver
3. Config'e ekle:
   ```yaml
   channels:
     discord:
       enabled: true
       token: "${DISCORD_BOT_TOKEN}"
   ```

---

### Adim 2.3: SlackAdapter

**Dosya:** `aethon/channels/slack_adapter.py`
**Kutuphane:** `slack-bolt>=1.18.0`

```python
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from aethon.channels.base import ChannelAdapter, InboundMessage, OutboundMessage

class SlackAdapter(ChannelAdapter):
    """Slack Bot adapter (slack-bolt + Socket Mode)."""

    def __init__(self, config, router):
        super().__init__(config, router)
        self.bot_token = config.channels.slack.bot_token
        self.app_token = config.channels.slack.app_token

        self.app = AsyncApp(token=self.bot_token)

        @self.app.event("message")
        async def handle_message(event, say):
            # Bot mesajlarini yoksay
            if event.get("bot_id"):
                return

            text = event.get("text", "")
            user_id = event.get("user", "unknown")
            thread_ts = event.get("thread_ts")

            inbound = InboundMessage(
                channel="slack",
                sender_id=user_id,
                sender_name=user_id,  # User info API ile zenginlestirilebilir
                text=text,
                thread_id=thread_ts,
                raw={"channel": event.get("channel"), "ts": event.get("ts")},
            )
            await self.on_message(inbound)

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            await handle_message(event, say)

    async def start(self) -> None:
        if not self.bot_token or not self.app_token:
            raise ValueError("Slack bot_token ve app_token gerekli")
        handler = AsyncSocketModeHandler(self.app, self.app_token)
        await handler.start_async()

    async def stop(self) -> None:
        pass

    async def send(self, message: OutboundMessage) -> None:
        channel = message.raw.get("channel") if hasattr(message, "raw") else message.recipient_id
        thread_ts = message.thread_id
        await self.app.client.chat_postMessage(
            channel=channel,
            text=message.text,
            thread_ts=thread_ts,
        )
```

**Kurulum:**
1. Slack App olustur → Bot Token + App Token al
2. Socket Mode etkinlestir
3. Event Subscriptions: `message.channels`, `message.im`, `app_mention`
4. Config'e ekle:
   ```yaml
   channels:
     slack:
       enabled: true
       bot_token: "${SLACK_BOT_TOKEN}"
       app_token: "${SLACK_APP_TOKEN}"
   ```

---

### Adim 2.4: WhatsAppAdapter

**Dosya:** `aethon/channels/whatsapp.py`
**Kutuphane:** `neonize` (pure Python) veya `whatsapp-web.js` bridge

**Not:** WhatsApp en karmasik adaptordur. Iki yaklasim:

**Yaklasim A: neonize (pure Python)**
```python
# Deneysel — neonize kutuphanesi yeni ve degisebilir
# QR kod eslestirme gerekli
# API stabil degil olabilir

class WhatsAppAdapter(ChannelAdapter):
    async def start(self):
        # neonize client olustur
        # QR kod goster (terminal)
        # Mesaj dinle
        ...
```

**Yaklasim B: whatsapp-web.js bridge (onerilen)**
```python
# Node.js subprocess olarak calisir
# Daha kararli ve topluluk destegi genis
# JSON-RPC veya stdio uzerinden iletisim

class WhatsAppAdapter(ChannelAdapter):
    async def start(self):
        # Node.js bridge subprocess baslat
        # stdin/stdout uzerinden JSON mesaj al/gonder
        ...
```

**Karar:** Faz 2'de ilk olarak neonize denenecek, sorun yasanirsa bridge'e gecilecek. WhatsApp en dusuk oncelikli kanal — diger 3 kanal (Telegram, Discord, Slack) oncelikli.

---

### Adim 2.5: Media Destegi

**Dosya:** `aethon/channels/base.py` (guncelleme)

Her adaptore media indirme/gonderme ekle:

```python
# Telegram ornegi — gorsel alma
@self.dp.message(F.photo)
async def handle_photo(tg_msg: types.Message):
    photo = tg_msg.photo[-1]  # En buyuk cozunurluk
    file = await self.bot.get_file(photo.file_id)
    file_path = file.file_path

    inbound = InboundMessage(
        channel="telegram",
        sender_id=str(tg_msg.from_user.id),
        sender_name=tg_msg.from_user.full_name,
        text=tg_msg.caption or "(gorsel)",
        media=[MediaAttachment(
            type="image",
            url=f"https://api.telegram.org/file/bot{self.token}/{file_path}",
            filename=f"{photo.file_id}.jpg",
            mime_type="image/jpeg",
        )],
    )
    await self.on_message(inbound)
```

---

### Adim 2.6: VectorMemory

**Dosya:** `aethon/memory/vector.py`

```python
import sqlite3
import json
import math
from datetime import datetime
from pathlib import Path

class VectorMemory:
    """SQLite + Ollama embedding tabanli uzun vadeli hafiza."""

    def __init__(self, db_path: str, ollama_host: str, model_id: str):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.db_path))
        self.ollama_host = ollama_host
        self.model_id = model_id
        self._create_tables()

    def _create_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                embedding TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.commit()

    def store(self, content: str, category: str = "general", metadata: dict | None = None):
        """Bilgi kaydet (embedding ile)."""
        embedding = self._get_embedding(content)
        self.db.execute(
            "INSERT INTO memories (content, category, embedding, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (content, category, json.dumps(embedding),
             json.dumps(metadata or {}), datetime.now().isoformat())
        )
        self.db.commit()

    def search(self, query: str, top_k: int = 5, category: str | None = None) -> list[dict]:
        """Semantik arama."""
        query_embedding = self._get_embedding(query)

        sql = "SELECT id, content, category, embedding, metadata, created_at FROM memories"
        params = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)

        rows = self.db.execute(sql, params).fetchall()

        scored = []
        for row_id, content, cat, emb_json, meta_json, created in rows:
            emb = json.loads(emb_json)
            score = self._cosine_similarity(query_embedding, emb)
            scored.append({
                "id": row_id,
                "content": content,
                "category": cat,
                "score": score,
                "metadata": json.loads(meta_json),
                "created_at": created,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def list_all(self, limit: int = 50) -> list[dict]:
        """Tum hafizalari listele."""
        rows = self.db.execute(
            "SELECT id, content, category, created_at FROM memories "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"id": r[0], "content": r[1], "category": r[2], "created_at": r[3]}
                for r in rows]

    def forget(self, memory_id: int):
        """Belirli bir hafizayi sil."""
        self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.commit()

    def _get_embedding(self, text: str) -> list[float]:
        """Ollama /api/embed endpoint'i ile embedding al."""
        import requests
        response = requests.post(
            f"{self.ollama_host}/api/embed",
            json={"model": self.model_id, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine benzerlik hesapla."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
```

---

### Adim 2.7: manage_memory Tool

**Dosya:** `aethon/tools/memory_tool.py`

```python
from strands import tool

@tool
def manage_memory(action: str, content: str = "", query: str = "",
                  category: str = "general", memory_id: int = 0) -> str:
    """Uzun vadeli hafizayi yonet.

    Args:
        action: "store" (kaydet), "search" (ara), "list" (listele), "forget" (unut)
        content: Kaydedilecek icerik (store icin)
        query: Aranacak sorgu (search icin)
        category: Kategori (store/search icin, varsayilan: "general")
        memory_id: Silinecek hafiza ID (forget icin)
    """
    from aethon.memory.vector import VectorMemory

    # Singleton pattern — runtime'dan alinacak
    memory = _get_memory_instance()

    if action == "store":
        if not content:
            return "Hata: 'content' parametresi gerekli."
        memory.store(content, category)
        return f"Hafizaya kaydedildi (kategori: {category})."

    elif action == "search":
        if not query:
            return "Hata: 'query' parametresi gerekli."
        results = memory.search(query, top_k=5, category=category if category != "general" else None)
        if not results:
            return "Sonuc bulunamadi."
        lines = []
        for r in results:
            lines.append(f"[{r['score']:.2f}] ({r['category']}) {r['content']}")
        return "\n".join(lines)

    elif action == "list":
        items = memory.list_all(limit=20)
        if not items:
            return "Hafiza bos."
        lines = [f"#{item['id']} ({item['category']}) {item['content'][:100]}" for item in items]
        return "\n".join(lines)

    elif action == "forget":
        if not memory_id:
            return "Hata: 'memory_id' parametresi gerekli."
        memory.forget(memory_id)
        return f"Hafiza #{memory_id} silindi."

    return f"Bilinmeyen action: {action}"
```

---

### Adim 2.8: SummarizingConversationManager Entegrasyonu

**Guncelleme:** `aethon/agent/runtime.py`

Faz 1'de zaten entegre edildi. Faz 2'de dogrulama ve fine-tuning:

```python
# AethonRuntime._create_conversation_manager
conv_mgr = SummarizingConversationManager(
    summary_ratio=0.3,              # Mesajlarin %30'unu ozetle
    preserve_recent_messages=10,     # Son 10 mesaji koru
    # summarization_agent=None,      # Varsayilan: ana agent ozetler
    # summarization_system_prompt=None,  # Varsayilan prompt
)
```

**Test senaryosu:** 20+ mesaj gonderdikten sonra context window asildisinda otomatik ozet olusturulmali.

---

### Adim 2.9: AethonSessionManager

**Dosya:** `aethon/session/manager.py`

```python
from strands.session import FileSessionManager
from pathlib import Path

class AethonSessionManager:
    """Kanal-bagli session yonetimi."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._instances: dict[str, FileSessionManager] = {}

    def get(self, session_id: str) -> FileSessionManager:
        """Session icin FileSessionManager al veya olustur."""
        if session_id not in self._instances:
            # Session ID'deki ozel karakterleri temizle
            safe_id = session_id.replace(":", "_").replace("/", "_")
            self._instances[session_id] = FileSessionManager(
                session_id=safe_id,
                storage_dir=str(self.storage_dir),
            )
        return self._instances[session_id]

    def resolve_session_id(self, channel: str, sender_id: str,
                           thread_id: str | None = None) -> str:
        """Kanal + sender'dan session ID olustur."""
        if thread_id:
            return f"{channel}:{thread_id}"
        return f"{channel}:{sender_id}"
```

---

### Adim 2.10: Gateway Guncellemesi

**Guncelleme:** `aethon/gateway/server.py`

```python
# Faz 2 — yeni adapterleri ekle

async def start(self):
    tasks = []

    # CLI
    if self.config.channels.cli.enabled:
        self.adapters["cli"] = CLIAdapter(self.config, self.router)
        tasks.append(self.adapters["cli"].start())

    # WebChat
    if self.config.channels.webchat.enabled:
        self.adapters["webchat"] = WebChatAdapter(self.config, self.router)
        tasks.append(self.adapters["webchat"].start())

    # Telegram
    if self.config.channels.telegram.enabled:
        from aethon.channels.telegram import TelegramAdapter
        self.adapters["telegram"] = TelegramAdapter(self.config, self.router)
        tasks.append(self.adapters["telegram"].start())

    # Discord
    if self.config.channels.discord.enabled:
        from aethon.channels.discord_adapter import DiscordAdapter
        self.adapters["discord"] = DiscordAdapter(self.config, self.router)
        tasks.append(self.adapters["discord"].start())

    # Slack
    if self.config.channels.slack.enabled:
        from aethon.channels.slack_adapter import SlackAdapter
        self.adapters["slack"] = SlackAdapter(self.config, self.router)
        tasks.append(self.adapters["slack"].start())

    # WhatsApp
    if self.config.channels.whatsapp.enabled:
        from aethon.channels.whatsapp import WhatsAppAdapter
        self.adapters["whatsapp"] = WhatsAppAdapter(self.config, self.router)
        tasks.append(self.adapters["whatsapp"].start())

    await asyncio.gather(*tasks)
```

---

## 3. Dogrulama Kontrol Listesi

```
[ ] Telegram'dan AETHON'a mesaj gonderip yanit alinabiyor
[ ] Discord'dan DM veya mention ile AETHON'a erisilme
[ ] Slack'ten Socket Mode ile mesajlasma
[ ] (Opsiyonel) WhatsApp QR eslestirme ve mesajlasma
[ ] Farkli kanallardan gelen mesajlar izole session'larda
[ ] "Bunu hatirla: X" → hafizaya kaydediliyor
[ ] "X hakkinda ne biliyorsun?" → hafizadan geri cagirilabiliyor
[ ] 20+ mesajdan sonra context yonetimi calisiyor
[ ] Media (gorsel) gonderildiginde tespit ediliyor
[ ] Tum kanallar config uzerinden etkin/devre disi yapilabiliyor
```
