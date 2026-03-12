# AETHON — Kisisel AI Asistan Sistemi Tasarim Dokumani

> **AETHON** (Autonomous Execution Through Harmonized Orchestrated Networks)
> Strands Agents SDK uzerine insa edilmis, OpenClaw'dan ilham alan ama onu asan kisisel AI asistan.
> Versiyon: 0.1 Draft | Tarih: 2026-03-12

---

## BOLUM 1: VIZYON

### 1.1 Ne Insa Ediyoruz?

AETHON, **kendi makinende calisan, tum mesajlasma kanallarindan erisilebilen, coklu-agent takimi tarafindan desteklenen kisisel bir AI asistan sistemidir.**

OpenClaw "AI agent'lar icin bir isletim sistemi" olarak kendini tanimlar. AETHON ise bunun otesine gecer:

> **OpenClaw = Gateway + Tek Agent + Skill'ler**
> **AETHON = Gateway + Agent Takimi + SOP Is Akislari + Yapilandirilmis Ciktilar**

### 1.2 Neden OpenClaw Degil?

| Sorun | OpenClaw | AETHON |
|-------|----------|--------|
| Guvenlik | CVE-2026-25253, 824+ zararli skill, WebSocket hijack | Loopback-only, skill marketi YOK, hook-tabanli policy |
| Agent Mimarisi | Tek agent (Pi — 4 tool) | Coklu uzman agent takimi (Swarm + Graph) |
| Is Akislari | Yok (agent kendi basina karar verir) | SOP-gudumlu yapilandirilmis akislar |
| Cikti Dogrulama | Yok | Pydantic ile zorunlu yapilandirilmis cikti |
| Dil | Node.js/TypeScript | Python 3.10+ (ML/AI ekosistemi ile dogal uyum) |
| Genisletilebilirlik | 21 tool template, karmasik | @tool dekoratoru — 1 satirda tool tanimla |
| Gozlemlenebilirlik | Sinirli | OpenTelemetry dahili |
| Model Destegi | Coklu (ama Pi-tabanli) | 11+ provider, sorunsuz degistirme |

### 1.3 Temel Ustunlukler

**1. Multi-Agent Takim (OpenClaw'da YOK)**
AETHON'da bir gorev geldiginde tek bir agent ugrasma — uzman bir takim devreye girer:
- **Arastirmaci Agent:** Web'de arastirma yapar, dokumantasyon okur
- **Kodcu Agent:** Kod yazar, test eder, debug eder
- **Analist Agent:** Veri analiz eder, grafik olusturur
- **Planlayici Agent:** Karmasik gorevleri adim adim boler

Bunlar `Swarm` ile isbirligi yapar veya `Graph` ile deterministik sirada calisir.

**2. SOP Is Akislari (OpenClaw'da YOK)**
Tekrarlanan gorevler icin standart operasyon prosedürleri:
- "Yeni proje baslat" → PDD SOP'u calisir, tasarim dokumani uretir
- "Bu kodu implement et" → Code-Assist SOP'u calisir, TDD ile kodlar
- "Haftalik rapor hazirla" → Ozel SOP, veri toplar, formatlar, gonderir

**3. Yapilandirilmis Cikti (OpenClaw'da YOK)**
Agent'in ciktisi Pydantic modeli ile dogrulanir:
```python
class MeetingNote(BaseModel):
    title: str
    attendees: list[str]
    action_items: list[ActionItem]
    next_meeting: datetime
```
Model bu formata uymak zorunda — hata varsa duzeltip tekrar dener.

**4. Guvenlik-Oncelikli Tasarim**
OpenClaw'un tum guvenlik sorunlarini bilerek tasarliyoruz:
- Marketplace YOK — tool'lar senin kontrolunde
- Gateway sadece localhost'ta
- Hook-tabanli tool onay mekanizmasi
- Sandbox izolasyonu

---

## BOLUM 2: MIMARI KARSILASTIRMA

### 2.1 Ozellik Tablosu

| Ozellik | OpenClaw | AETHON | Avantaj |
|---------|----------|--------|---------|
| **Runtime** | Node.js 22+ | Python 3.10+ | AETHON — ML/AI ekosistemi |
| **Agent Framework** | Pi (ozel, 4 tool) | Strands Agents (70+ tool) | AETHON — 17x fazla tool |
| **Model Provider** | Anthropic, OpenAI, Ollama | 11+ provider (Bedrock, Anthropic, OpenAI, Ollama, Gemini, LiteLLM, Mistral, vb.) | AETHON — daha genis |
| **Multi-Agent** | YOK | Swarm + Graph + Agent-as-Tool | AETHON |
| **SOP/Workflow** | YOK | 5 dahili SOP + ozel SOP yazma | AETHON |
| **Structured Output** | YOK | Pydantic dogrulama | AETHON |
| **Tool Tanimlama** | SKILL.md (markdown) | @tool dekoratoru (Python) | AETHON — tip guvenligi |
| **Mesajlasma** | 22+ kanal | 6 kanal (moduler, genisletilebilir) | OpenClaw — daha fazla (su an) |
| **Hafiza** | SQLite + Vector | FileSession + Vector (genisletilebilir) | Esit |
| **Guvenlik** | Ciddi aciklar (CVE'ler) | Tasarimdan guvenli | AETHON |
| **Gozlemlenebilirlik** | Sinirli | OpenTelemetry | AETHON |
| **Ses** | ElevenLabs TTS/STT | Bidi Streaming (Nova Sonic, Gemini Live) | AETHON — gercek zamanli |
| **Human-in-the-Loop** | Sinirli | Interrupt mekanizmasi | AETHON |
| **Hooks/Extension** | Pi extensions (5 event) | 8+ event, Plugin sistemi | AETHON |
| **Canvas/UI** | A2UI (agent-gudumlu HTML) | WebChat + FastAPI dashboard | Farkli yaklasim |
| **Cron/Zamanlama** | Config-tabanli | SOP + Python cron | Esit |

---

## BOLUM 3: CEKIRDEK MIMARI

### 3.1 Yuksek Seviye Mimari

```
╔══════════════════════════════════════════════════════════════════╗
║                        AETHON SISTEMI                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │                    GATEWAY KATMANI                       │    ║
║  │            (Python asyncio + WebSocket)                  │    ║
║  │                                                          │    ║
║  │  ┌─────┐ ┌────┐ ┌───────┐ ┌─────┐ ┌───────┐ ┌───┐    │    ║
║  │  │Whats│ │Tele│ │Discord│ │Slack│ │WebChat│ │CLI│      │    ║
║  │  │App  │ │gram│ │       │ │     │ │       │ │   │      │    ║
║  │  └──┬──┘ └─┬──┘ └──┬────┘ └──┬──┘ └──┬────┘ └─┬─┘    │    ║
║  │     └──────┴───────┴────┬────┴───────┴────────┘        │    ║
║  └─────────────────────────┼───────────────────────────────┘    ║
║                            │                                     ║
║                   ┌────────▼────────┐                            ║
║                   │  MESSAGE ROUTER  │                           ║
║                   │ (Session + Auth)  │                          ║
║                   └────────┬────────┘                            ║
║                            │                                     ║
║  ┌─────────────────────────▼───────────────────────────────┐    ║
║  │                   AGENT KATMANI                          │    ║
║  │                                                          │    ║
║  │  ┌──────────────────────────────────────────────┐       │    ║
║  │  │            ORCHESTRATOR AGENT                  │      │    ║
║  │  │    (Strands Agent — Ana Yonlendirici)          │     │    ║
║  │  └────────────────────┬───────────────────────────┘     │    ║
║  │                       │                                  │    ║
║  │       ┌───────────────┼───────────────┐                 │    ║
║  │       │               │               │                  │    ║
║  │  ┌────▼────┐   ┌─────▼─────┐  ┌─────▼─────┐           │    ║
║  │  │Kodcu    │   │Arastirmaci│  │ Analist   │            │    ║
║  │  │Agent    │   │Agent      │  │ Agent     │            │    ║
║  │  │(Swarm)  │   │(Swarm)    │  │ (Swarm)   │           │    ║
║  │  └─────────┘   └───────────┘  └───────────┘            │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                            │                                     ║
║  ┌─────────────────────────▼───────────────────────────────┐    ║
║  │                  ALTYAPI KATMANI                         │    ║
║  │                                                          │    ║
║  │  ┌────────┐  ┌────────┐  ┌──────┐  ┌────────────────┐  │    ║
║  │  │ Hafiza │  │Session │  │Config│  │  Ollama/Model  │  │    ║
║  │  │(Vector)│  │Manager │  │      │  │  Provider      │  │    ║
║  │  └────────┘  └────────┘  └──────┘  └────────────────┘  │    ║
║  └─────────────────────────────────────────────────────────┘    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### 3.2 Katmanlar

| Katman | Sorumluluk | Teknoloji |
|--------|-----------|-----------|
| **Gateway** | Mesaj alma/gonderme, kanal adapterleri, WebSocket sunucu | Python asyncio, aiohttp |
| **Message Router** | Session eslestirme, kimlik dogrulama, mesaj kuyrugu | asyncio.Queue, routing tablosu |
| **Agent** | LLM etkilesimi, tool calistirma, multi-agent orkestrasyon | Strands Agents SDK |
| **Altyapi** | Hafiza, session, config, model provider | FileSessionManager, SQLite, YAML |

### 3.3 Veri Akisi (Uctan Uca)

```
1. Kullanici WhatsApp'tan mesaj gonderir
   │
2. WhatsApp Adapter mesaji alir, normalize eder
   │  → InboundMessage(channel="whatsapp", sender="user", text="...", media=None)
   │
3. Message Router:
   │  a. Kimlik dogrula (allowlist kontrolu)
   │  b. Session bul veya olustur (channel:sender → session_id)
   │  c. Mesaj kuyrukleme (asyncio.Queue)
   │
4. Agent Katmani:
   │  a. Session'dan konusma gecmisini yukle
   │  b. System prompt birlesim (SOUL.md + TOOLS.md + workspace context)
   │  c. Strands Agent cagir: agent(message)
   │  d. Agent loop: Model → Tool → Model → ... → end_turn
   │  e. Hooks atesle (BeforeToolCall, AfterToolCall, vb.)
   │  f. Session'a kaydet
   │
5. Yanit Message Router'a doner
   │  → OutboundMessage(channel="whatsapp", recipient="user", text="...", media=None)
   │
6. WhatsApp Adapter yaniti gonderir
```

---

## BOLUM 4: GATEWAY VE KANAL ADAPTER SISTEMI

### 4.1 Gateway Sunucu

Gateway, tum kanal adaptorlerini koordine eden **tek bir asyncio sureci**dir.

```python
# aethon/gateway/server.py

import asyncio
from aethon.gateway.router import MessageRouter
from aethon.channels import WhatsAppAdapter, TelegramAdapter, DiscordAdapter
from aethon.channels import SlackAdapter, WebChatAdapter, CLIAdapter

class AethonGateway:
    """AETHON ana gateway sunucusu."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.router = MessageRouter(config)
        self.adapters: dict[str, ChannelAdapter] = {}

    async def start(self):
        """Tum etkin kanallari baslat."""
        if self.config.channels.whatsapp.enabled:
            self.adapters["whatsapp"] = WhatsAppAdapter(self.config, self.router)
        if self.config.channels.telegram.enabled:
            self.adapters["telegram"] = TelegramAdapter(self.config, self.router)
        if self.config.channels.discord.enabled:
            self.adapters["discord"] = DiscordAdapter(self.config, self.router)
        if self.config.channels.slack.enabled:
            self.adapters["slack"] = SlackAdapter(self.config, self.router)

        # WebChat her zaman aktif (kontrol paneli)
        self.adapters["webchat"] = WebChatAdapter(self.config, self.router)
        self.adapters["cli"] = CLIAdapter(self.config, self.router)

        # Tum adapterleri paralel olarak baslat
        tasks = [adapter.start() for adapter in self.adapters.values()]
        await asyncio.gather(*tasks)

    async def shutdown(self):
        """Tum adapterleri duzenli kapat."""
        for adapter in self.adapters.values():
            await adapter.stop()
```

### 4.2 Channel Adapter Arayuzu

Tum kanallar ayni arayuzu uygular:

```python
# aethon/channels/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class InboundMessage:
    """Normalize edilmis gelen mesaj."""
    channel: str                    # "whatsapp", "telegram", "discord", vb.
    sender_id: str                  # Kanal-spesifik kullanici ID
    sender_name: str                # Goruntulenen isim
    text: str                       # Mesaj metni
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None  # Yanitlanan mesaj ID
    thread_id: Optional[str] = None # Thread/konu ID
    timestamp: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)  # Platform-spesifik ham veri

@dataclass
class OutboundMessage:
    """Normalize edilmis giden mesaj."""
    channel: str
    recipient_id: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None

@dataclass
class MediaAttachment:
    """Medya eki."""
    type: str            # "image", "audio", "video", "document"
    url: Optional[str] = None
    data: Optional[bytes] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None

class ChannelAdapter(ABC):
    """Tum kanal adapterleri icin temel sinif."""

    def __init__(self, config, router):
        self.config = config
        self.router = router

    @abstractmethod
    async def start(self) -> None:
        """Kanal dinlemeye basla."""

    @abstractmethod
    async def stop(self) -> None:
        """Kanali duzenli kapat."""

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None:
        """Mesaj gonder."""

    async def on_message(self, message: InboundMessage) -> None:
        """Gelen mesaji router'a ilet (tum adapterler bu metodu cagirir)."""
        response = await self.router.handle(message)
        if response:
            await self.send(response)
```

### 4.3 Kanal Implementasyonlari

#### WhatsApp Adapter

```python
# aethon/channels/whatsapp.py
# Kutuphane: neonize (Python native WhatsApp Web)
# Alternatif: whatsapp-web.js bridge (Node.js subprocess)

class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp Web baglantisi."""

    async def start(self):
        # neonize ile QR kod eslestirme
        # Gelen mesajlari dinle
        # Media indirme destegi
        ...

    async def send(self, message: OutboundMessage):
        # Metin, gorsel, dosya gonderme
        # Reply threading
        ...
```

| Kanal | Python Kutuphanesi | Baglanti Yontemi | Notlar |
|-------|--------------------|-----------------|--------|
| **WhatsApp** | `neonize` veya `whatsapp-web.js` bridge | QR kod eslestirme | neonize pure Python, bridge daha kararli |
| **Telegram** | `python-telegram-bot` veya `aiogram` | Bot Token (BotFather) | aiogram asyncio-native, tercih edilir |
| **Discord** | `discord.py` veya `nextcord` | Bot Token (Developer Portal) | discord.py 2.0+ asyncio-native |
| **Slack** | `slack-bolt` (Python) | Bot Token + App Token | Socket Mode icin app token gerekli |
| **WebChat** | `FastAPI` + `websockets` | HTTP/WS (localhost) | Kontrol paneli olarak da hizmet eder |
| **CLI** | `prompt_toolkit` | Terminal stdin/stdout | Gelistirme ve debug icin |

#### Telegram Adapter Ornegi

```python
# aethon/channels/telegram.py

from aiogram import Bot, Dispatcher, types

class TelegramAdapter(ChannelAdapter):
    async def start(self):
        self.bot = Bot(token=self.config.channels.telegram.token)
        self.dp = Dispatcher()

        @self.dp.message()
        async def handle_message(tg_msg: types.Message):
            inbound = InboundMessage(
                channel="telegram",
                sender_id=str(tg_msg.from_user.id),
                sender_name=tg_msg.from_user.full_name,
                text=tg_msg.text or "",
                timestamp=tg_msg.date,
            )
            await self.on_message(inbound)

        await self.dp.start_polling(self.bot)

    async def send(self, message: OutboundMessage):
        await self.bot.send_message(
            chat_id=int(message.recipient_id),
            text=message.text,
            reply_to_message_id=message.reply_to
        )
```

### 4.4 WebChat + Kontrol Paneli

WebChat adaptoru ayni zamanda AETHON'un web arayuzudur:

```python
# aethon/channels/webchat.py

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

class WebChatAdapter(ChannelAdapter):
    def __init__(self, config, router):
        super().__init__(config, router)
        self.app = FastAPI(title="AETHON Control Panel")

        # Statik dosyalar (dashboard UI)
        self.app.mount("/ui", StaticFiles(directory="aethon/ui/dist"), name="ui")

        # WebSocket chat endpoint
        @self.app.websocket("/ws/chat")
        async def ws_chat(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive_text()
                inbound = InboundMessage(
                    channel="webchat",
                    sender_id="local-user",
                    sender_name="User",
                    text=data
                )
                response = await self.router.handle(inbound)
                if response:
                    await websocket.send_text(response.text)

        # REST API — durum, config, session'lar
        @self.app.get("/api/status")
        async def status():
            return {"channels": list(gateway.adapters.keys()), "uptime": ...}

    async def start(self):
        import uvicorn
        config = uvicorn.Config(self.app, host="127.0.0.1", port=18790)
        server = uvicorn.Server(config)
        await server.serve()
```

---

## BOLUM 5: AGENT RUNTIME

### 5.1 Strands Agent Entegrasyonu

AETHON'un beyni Strands Agent'tir. OpenClaw'un Pi Agent'i sadece 4 tool'a sahipken, AETHON 70+ tool ve coklu agent destegi sunar.

```python
# aethon/agent/runtime.py

from strands import Agent, tool
from strands.models.ollama import OllamaModel
from strands.session import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager

class AethonRuntime:
    """AETHON agent calisma zamani."""

    def __init__(self, config: AethonConfig):
        self.config = config
        self.model = self._create_model()
        self.session_manager = FileSessionManager(base_dir=config.paths.sessions_dir)
        self.agents: dict[str, Agent] = {}

    def _create_model(self) -> OllamaModel:
        return OllamaModel(
            host=self.config.model.host,          # "http://localhost:11434"
            model_id=self.config.model.model_id,   # "qwen3-coder-next"
            temperature=self.config.model.temperature,  # 1.0
            top_p=self.config.model.top_p,         # 0.95
            options={"top_k": self.config.model.top_k}  # 40
        )

    def get_or_create_agent(self, session_id: str) -> Agent:
        """Session icin agent al veya olustur."""
        if session_id not in self.agents:
            system_prompt = self._compose_system_prompt(session_id)
            self.agents[session_id] = Agent(
                model=self.model,
                system_prompt=system_prompt,
                tools=self._get_tools(),
                session_manager=self.session_manager,
                conversation_manager=SummarizingConversationManager(
                    max_messages=50,
                    summary_ratio=0.5,
                    preserve_recent_messages=10,
                ),
                hooks=[SecurityHookProvider(), TelemetryHookProvider()],
                id=session_id,
                name="AETHON Assistant",
            )
        return self.agents[session_id]

    async def process(self, message: InboundMessage, session_id: str) -> str:
        """Mesaji isle ve yanit dondur."""
        agent = self.get_or_create_agent(session_id)
        result = await agent.invoke_async(message.text)
        return result.message["content"][0]["text"]
```

### 5.2 System Prompt Katmanlari

OpenClaw'un AGENTS.md + SOUL.md + TOOLS.md yaklasimindan ilham alan ama daha guclu bir sistem:

```
aethon/
  workspace/
    SOUL.md          → Agent kisiligi ve davranis kurallari
    TOOLS.md         → Kullanici tercihleri ve konvansiyonlar
    CONTEXT.md       → Proje/is baglami (otomatik guncellenir)
    sops/            → Aktif SOP'lar
    memory/          → Uzun vadeli hafiza dosyalari
```

```python
# aethon/agent/prompt.py

def compose_system_prompt(config, session_id: str) -> str:
    """Katmanli system prompt olustur."""

    layers = []

    # 1. Cekirdek kisilik
    soul = read_file(config.paths.workspace / "SOUL.md")
    layers.append(f"## Kisilik\n{soul}")

    # 2. Kullanici tercihleri
    tools_md = read_file(config.paths.workspace / "TOOLS.md")
    layers.append(f"## Kullanici Tercihleri\n{tools_md}")

    # 3. Mevcut baglam
    context = read_file(config.paths.workspace / "CONTEXT.md")
    layers.append(f"## Mevcut Baglam\n{context}")

    # 4. Aktif SOP'lar (sadece ozet listesi — tam icerik lazim olunca yuklenir)
    sop_list = list_sops(config.paths.workspace / "sops")
    if sop_list:
        sop_summary = "\n".join(f"- /{s.name}: {s.description}" for s in sop_list)
        layers.append(f"## Kullanilabilir Is Akislari\n{sop_summary}")

    # 5. Kanal bilgisi
    layers.append(f"## Aktif Kanal\nSession: {session_id}")

    # 6. Zaman
    from datetime import datetime
    layers.append(f"## Zaman\n{datetime.now().isoformat()}")

    return "\n\n---\n\n".join(layers)
```

**SOUL.md Ornegi:**
```markdown
# AETHON — Kisilik Tanimlamasi

Sen AETHON, Mert'in kisisel AI asistanisin. Mac uzerinde Ollama ile calisiyorsun.

## Davranis Kurallari
- Turkce ve Ingilizce konusabilirsin. Mert hangi dilde yazarsa o dilde yanit ver.
- Kisa ve oz yanit ver. Gereksiz aciklama yapma.
- Kod yazarken yorum ekleme — kod kendini aciklamali.
- Hata yaptiginda kabul et ve duzelt.
- Emin olmadigin seylerde "emin degilim" de.

## Uzmanlik Alanlari
- Python backend gelistirme (asyncio, WebSocket, OOP)
- AI/ML agent sistemleri
- DevOps ve otomasyon

## Sinirlar
- Internete dogrudan erisimin yok (tool uzerinden eris).
- Dosya islemleri workspace dizini ile sinirli.
```

### 5.3 Tool Pipeline

OpenClaw'un 7 katmanli tool pipeline'ini Strands hooks ile daha temiz uyguluyoruz:

```python
# aethon/agent/hooks/security.py

from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent, HookProvider, HookRegistry

class SecurityHookProvider(HookProvider):
    """Tool cagrilarini guvenlik politikalarina gore filtrele."""

    DANGEROUS_TOOLS = {"shell", "file_write", "editor", "use_aws"}
    BLOCKED_COMMANDS = {"rm -rf /", "sudo", "mkfs", "dd if="}

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self.check_tool_safety)
        registry.add_callback(AfterToolCallEvent, self.log_tool_result)

    def check_tool_safety(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # Tehlikeli komut kontrolu
        if tool_name == "shell":
            command = tool_input.get("command", "")
            for blocked in self.BLOCKED_COMMANDS:
                if blocked in command:
                    event.cancel_tool = f"Engellendi: '{blocked}' iceren komutlar guvenlik nedeniyle yasakli."
                    return

        # Workspace disina dosya erisimi engelle
        if tool_name in ("file_read", "file_write", "editor"):
            path = tool_input.get("path", "") or tool_input.get("file_path", "")
            if not self._is_within_workspace(path):
                event.cancel_tool = f"Engellendi: Workspace disi dosya erisimi ({path})"

    def log_tool_result(self, event: AfterToolCallEvent) -> None:
        """Tum tool sonuclarini logla."""
        import logging
        logger = logging.getLogger("aethon.tools")
        status = "HATA" if event.exception else "OK"
        logger.info(f"Tool: {event.tool_use['name']} | Durum: {status}")

    def _is_within_workspace(self, path: str) -> bool:
        from pathlib import Path
        try:
            resolved = Path(path).resolve()
            workspace = Path(self.config.paths.workspace).resolve()
            return str(resolved).startswith(str(workspace))
        except Exception:
            return False
```

### 5.4 Tool Ekosistemi

AETHON'un kullanabilecegi tool'lar:

**Strands Dahili (strands-agents-tools):**

| Kategori | Tool'lar |
|----------|---------|
| Dosya | `file_read`, `file_write`, `editor` |
| Shell | `shell`, `python_repl` |
| Web | `http_request`, `tavily_search`, `browser` |
| Matematik | `calculator` |
| Dusunme | `think` (cok-dongulu recursive analiz) |
| Hafiza | `memory`, `mem0_memory` |
| Iletisim | `slack` |
| Otomasyon | `cron`, `workflow`, `batch` |

**AETHON Ozel Tool'lari:**

```python
# aethon/tools/messaging.py

@tool
def send_message(channel: str, recipient: str, text: str) -> dict:
    """Belirtilen kanala mesaj gonder.

    Args:
        channel: Hedef kanal ("whatsapp", "telegram", "discord", "slack")
        recipient: Alici ID veya isim
        text: Gonderilecek mesaj
    """
    # Gateway uzerinden mesaj gonder
    gateway = get_gateway_instance()
    adapter = gateway.adapters.get(channel)
    if not adapter:
        return {"status": "error", "content": [{"text": f"Kanal bulunamadi: {channel}"}]}

    outbound = OutboundMessage(channel=channel, recipient_id=recipient, text=text)
    asyncio.create_task(adapter.send(outbound))
    return {"status": "success", "content": [{"text": f"Mesaj {channel} uzerinden gonderildi."}]}


@tool
def schedule_task(cron_expression: str, task_description: str) -> dict:
    """Zamanlanmis gorev olustur.

    Args:
        cron_expression: Cron ifadesi (orn: "0 9 * * 1-5" = hafta ici her sabah 9)
        task_description: Gorev aciklamasi
    """
    scheduler = get_scheduler_instance()
    task_id = scheduler.add(cron_expression, task_description)
    return {"status": "success", "content": [{"text": f"Gorev zamanlandi: {task_id}"}]}


@tool
def manage_memory(action: str, content: str = "", query: str = "") -> dict:
    """Uzun vadeli hafizayi yonet.

    Args:
        action: "store" (kaydet), "search" (ara), "list" (listele), "forget" (unut)
        content: Kaydedilecek icerik (store icin)
        query: Aranacak sorgu (search icin)
    """
    memory = get_memory_instance()
    if action == "store":
        memory.store(content)
        return {"status": "success", "content": [{"text": "Hafizaya kaydedildi."}]}
    elif action == "search":
        results = memory.search(query, top_k=5)
        return {"status": "success", "content": [{"text": "\n".join(results)}]}
    ...
```

---

## BOLUM 6: MULTI-AGENT USTUNLUGU

Bu, AETHON'un OpenClaw'a karsi en buyuk avantaji. OpenClaw tek bir agent ile calisir — AETHON bir takim kurar.

### 6.1 Uzman Agent Takimi

```python
# aethon/agents/specialists.py

from strands import Agent
from strands.models.ollama import OllamaModel
from strands_tools import file_read, file_write, editor, shell, http_request
from strands_tools import calculator, python_repl, think

def create_specialist_agents(model: OllamaModel) -> dict[str, Agent]:
    """Uzman agent takimi olustur."""

    coder = Agent(
        model=model,
        system_prompt="""Sen bir yazilim gelistirme uzmanisin.
        Gorevlerin: kod yazma, test etme, debug etme, refactoring.
        TDD prensiplerini takip et. Once test yaz, sonra implement et.
        Kisa, temiz, yorumsuz kod yaz.""",
        tools=[file_read, file_write, editor, shell, python_repl, think],
        name="Kodcu",
    )

    researcher = Agent(
        model=model,
        system_prompt="""Sen bir arastirma uzmanisin.
        Gorevlerin: web arastirmasi, dokumantasyon okuma, bilgi toplama.
        Kaynaklari belirt. Ozet ve analizle sun.""",
        tools=[http_request, file_read, think],
        name="Arastirmaci",
    )

    analyst = Agent(
        model=model,
        system_prompt="""Sen bir veri analisti ve raporlamacisin.
        Gorevlerin: veri analizi, grafik olusturma, rapor yazma.
        Net, olculebilir sonuclar sun.""",
        tools=[python_repl, calculator, file_read, file_write, think],
        name="Analist",
    )

    planner = Agent(
        model=model,
        system_prompt="""Sen bir proje planlayicisisin.
        Gorevlerin: karmasik gorevleri adim adim bolme, onceliklendirme.
        Her adimi net ve uygulanabilir yap.""",
        tools=[file_read, file_write, think],
        name="Planlayici",
    )

    return {
        "coder": coder,
        "researcher": researcher,
        "analyst": analyst,
        "planner": planner,
    }
```

### 6.2 Swarm Kullanimi (Isbirligi)

Birden fazla uzmanin bir arada calisarak gorevi tamamlamasi:

```python
# aethon/agents/teams.py

from strands.multiagent import Swarm

class TeamOrchestrator:
    """Uzman agent takimlarini yonet."""

    def __init__(self, specialists: dict[str, Agent], orchestrator: Agent):
        self.specialists = specialists
        self.orchestrator = orchestrator

    async def collaborative_task(self, task: str) -> str:
        """Isbirlikci gorev — agent'lar birbirine devir teslim yapar."""
        swarm = Swarm(
            nodes=list(self.specialists.values()),
            entry_point=self.orchestrator,
            max_handoffs=10,
            max_iterations=10,
            execution_timeout=300.0,  # 5 dakika
        )
        result = swarm(task)
        return self._extract_final_answer(result)

    async def pipeline_task(self, task: str) -> str:
        """Pipeline gorev — sirayla calisir (Planlama → Arastirma → Kodlama)."""
        from strands.multiagent import GraphBuilder

        builder = GraphBuilder()
        plan_node = builder.add_node(self.specialists["planner"], "planlama")
        research_node = builder.add_node(self.specialists["researcher"], "arastirma")
        code_node = builder.add_node(self.specialists["coder"], "kodlama")

        builder.add_edge(plan_node, research_node)
        builder.add_edge(research_node, code_node)
        builder.set_entry_points(plan_node)

        graph = builder.build()
        result = graph(task)
        return self._extract_final_answer(result)
```

### 6.3 Agent-as-Tool Deseni

Ana agent, uzman agent'lari tool olarak cagirir:

```python
# aethon/tools/delegate.py

from strands import tool

@tool
def ask_coder(task: str) -> dict:
    """Kodlama gorevini kodcu uzmanina devret.

    Args:
        task: Kodlama gorevi aciklamasi
    """
    coder = get_specialist("coder")
    result = coder(task)
    return {"status": "success", "content": [{"text": result.message["content"][0]["text"]}]}

@tool
def ask_researcher(query: str) -> dict:
    """Arastirma gorevini arastirmaci uzmanina devret.

    Args:
        query: Arastirilacak konu
    """
    researcher = get_specialist("researcher")
    result = researcher(query)
    return {"status": "success", "content": [{"text": result.message["content"][0]["text"]}]}

@tool
def ask_analyst(data_task: str) -> dict:
    """Veri analizi gorevini analiste devret.

    Args:
        data_task: Analiz gorevi aciklamasi
    """
    analyst = get_specialist("analyst")
    result = analyst(data_task)
    return {"status": "success", "content": [{"text": result.message["content"][0]["text"]}]}
```

### 6.4 Kullanici Deneyimi

```
Kullanici (WhatsApp):
  "Bu projedeki performans sorunlarini bul ve duzelt"

AETHON Orchestrator:
  → Planlayici Agent'a devret: "Gorevi adim adim bol"
  ← Plan: 1) Profiling 2) Analiz 3) Optimizasyon 4) Test

  → Kodcu Agent'a devret: "Profiling yap"
  ← Profiling sonuclari

  → Analist Agent'a devret: "Bu profiling sonuclarini analiz et"
  ← Analiz raporu: "3 darboğaz tespit edildi"

  → Kodcu Agent'a devret: "Bu 3 darbogazi optimize et"
  ← Optimizasyon yapildi, testler gecti

AETHON → Kullaniciya (WhatsApp):
  "3 performans darbogazi bulundu ve duzeltildi:
   1. N+1 sorgu problemi → Batch query'ye cevirildi
   2. Gereksiz loop → Vectorized isleme
   3. Bellek sizintisi → Context manager eklendi
   Tum testler gecti."
```

---

## BOLUM 7: SOP ENTEGRASYONU

### 7.1 AETHON SOP Sistemi

OpenClaw'da SOP benzeri yapilar yok. AETHON, Strands Agent SOP'larini dogrudan entegre eder ve ozel SOP'lar yazma imkani sunar.

```
aethon/
  workspace/
    sops/
      code-assist.sop.md      # Dahili: TDD-tabanli kod implementasyonu
      pdd.sop.md               # Dahili: Prompt-Driven Development
      weekly-report.sop.md     # Ozel: Haftalik rapor hazirla
      deploy-check.sop.md     # Ozel: Dagitim oncesi kontrol listesi
      morning-brief.sop.md    # Ozel: Sabah brifing SOP'u
```

### 7.2 Ozel SOP Ornegi

```markdown
# morning-brief.sop.md
---
name: morning-brief
description: Her sabah kisisel brifing hazirla
user-invocable: true
---

# Sabah Brifing

## Overview
Her sabah calismaya baslamadan once kisa bir brifing hazirlar.

## Parameters
- **date** (optional, default: bugun): Brifing tarihi

## Steps

### 1. Takvim Kontrolu
Bugunun takvim etkinliklerini kontrol et.

**Constraints:**
- You MUST bugunun tum etkinliklerini listele
- You SHOULD oncelik sirasina gore sirala

### 2. Bekleyen Gorevler
Acik gorevleri ve deadline'lari kontrol et.

**Constraints:**
- You MUST github issue'lari ve PR'lari kontrol et
- You SHOULD geciken gorevleri vurgula

### 3. Haber ve Gundem
Ilgili teknoloji haberlerini ozetle.

**Constraints:**
- You SHOULD en fazla 5 haber basligi sun
- You MUST kaynaklari belirt

### 4. Brifing Formatla
Tum bilgileri kisa ve net bir brifing olarak formatla.

**Constraints:**
- You MUST toplam 200 kelimeyi gecme
- You SHOULD oncelikleri vurgula
```

### 7.3 SOP Tetikleme

```
Kullanici: "/morning-brief"

AETHON:
  1. SOP dosyasini yukle
  2. System prompt'a SOP talimatlarini ekle
  3. SOP adimlarini sirayla calistir
  4. Sonucu kullaniciya gonder

Kullanici: "/code-assist task=login-form-fix"

AETHON:
  1. Code-Assist SOP yukle
  2. Explore → Plan → Code → Commit faslarini izle
  3. Her fazda ilgili uzman agent'i kullan
  4. PR olustur, sonucu bildir
```

---

## BOLUM 8: HAFIZA VE DURUM YONETIMI

### 8.1 Uc Katmanli Hafiza

```
┌─────────────────────────────────────┐
│         UZUN VADELI HAFIZA          │
│   (SQLite + Vector Embeddings)      │
│   Kullanici tercihleri, bilgiler,   │
│   ogrenilen kaliplar                │
│   → Aylar/yillar boyunca kalir      │
├─────────────────────────────────────┤
│          SESSION HAFIZA             │
│     (FileSessionManager)            │
│   Konusma gecmisi, agent state      │
│   → Session boyunca kalir           │
├─────────────────────────────────────┤
│        CALISMA HAFIZA               │
│      (Conversation Manager)         │
│   Son N mesaj + ozet                │
│   → Her model cagrisinda            │
└─────────────────────────────────────┘
```

### 8.2 Session Stratejisi

```python
# aethon/session/manager.py

class AethonSessionManager:
    """Kanal-bagli session yonetimi."""

    def resolve_session_id(self, message: InboundMessage) -> str:
        """Mesajdan session ID olustur.

        Tek kullanici sistemi oldugu icin basit:
        - DM: "main" (tek ana session)
        - Farkli kanal: "{channel}:{sender_id}" (kanal basina session)
        - Thread: "{channel}:{thread_id}" (thread basina session)
        """
        if message.thread_id:
            return f"{message.channel}:{message.thread_id}"
        return f"{message.channel}:{message.sender_id}"
```

### 8.3 Vektorel Hafiza

```python
# aethon/memory/vector.py

import sqlite3
import json

class VectorMemory:
    """SQLite + embedding tabanli uzun vadeli hafiza."""

    def __init__(self, db_path: str, model: OllamaModel):
        self.db = sqlite3.connect(db_path)
        self.model = model
        self._create_tables()

    def store(self, content: str, category: str = "general", metadata: dict = None):
        """Bilgi kaydet (embedding ile)."""
        embedding = self._get_embedding(content)
        self.db.execute(
            "INSERT INTO memories (content, category, embedding, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (content, category, json.dumps(embedding), json.dumps(metadata or {}), datetime.now().isoformat())
        )
        self.db.commit()

    def search(self, query: str, top_k: int = 5) -> list[str]:
        """Semantik arama."""
        query_embedding = self._get_embedding(query)
        # Cosine similarity ile en yakin sonuclari bul
        all_memories = self.db.execute("SELECT content, embedding FROM memories").fetchall()
        scored = [(content, self._cosine_sim(query_embedding, json.loads(emb)))
                  for content, emb in all_memories]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [content for content, score in scored[:top_k]]

    def _get_embedding(self, text: str) -> list[float]:
        """Ollama embedding API kullan."""
        import requests
        response = requests.post(
            f"{self.model.host}/api/embed",
            json={"model": self.model.model_id, "input": text}
        )
        return response.json()["embeddings"][0]
```

---

## BOLUM 9: GUVENLIK MODELI

### 9.1 OpenClaw Guvenlik Sorunlari ve AETHON Cozumleri

| OpenClaw Sorunu | AETHON Cozumu |
|-----------------|---------------|
| CVE-2026-25253 (WebSocket hijack) | Gateway sadece 127.0.0.1'e baglanir, dis erisim YOK |
| ClawHub zararli skill'ler | Marketplace YOK — tum tool'lar yerel, senin kontrolunde |
| Paylasimli global context | Tek kullanici sistemi — paylasim sorunu yok |
| Prompt injection via email/web | Hook-tabanli icerik filtreleme, tool onay mekanizmasi |
| Cross-session veri sizintisi | Session izolasyonu, workspace sinirlamasi |
| Self-modifying davranis | Hook ile degisiklikleri dogrula/engelle |
| Genis sistem izinleri | SecurityHookProvider ile workspace-only erisim |
| Hafiza zehirlenmesi | Hafiza yazma onay mekanizmasi |

### 9.2 Guvenlik Katmanlari

```python
# 1. AG KATMANI
# Gateway sadece localhost'ta — dis erisim imkansiz
host = "127.0.0.1"  # ASLA "0.0.0.0" DEGIL

# 2. TOOL KATMANI
# BeforeToolCallEvent hook'u ile tehlikeli islemler engellenir
class SecurityHookProvider:
    def check_tool_safety(self, event: BeforeToolCallEvent):
        # Workspace disi dosya erisimi engelle
        # Tehlikeli shell komutlari engelle
        # Ag islemleri logla

# 3. HAFIZA KATMANI
# Hafizaya yazma oncesi dogrulama
class MemoryGuardHook:
    def before_memory_write(self, event):
        # Hassas bilgi tespiti (API key, sifre, vb.)
        # Zararli talimat tespiti

# 4. ICERIK KATMANI
# Dis kaynaklardan gelen icerik filtreleme
class ContentFilterHook:
    def filter_external_content(self, content: str) -> str:
        # HTML/script injection temizleme
        # Prompt injection tespiti
```

### 9.3 Tool Onay Mekanizmasi

```python
# aethon/agent/hooks/approval.py

from strands.hooks import BeforeToolCallEvent
from strands.interrupt import Interrupt, InterruptException

class ApprovalHookProvider(HookProvider):
    """Tehlikeli tool'lar icin kullanici onayi iste."""

    REQUIRES_APPROVAL = {"shell", "file_write", "use_aws", "send_message"}

    def check_approval(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use["name"]
        if tool_name in self.REQUIRES_APPROVAL:
            interrupt = Interrupt(
                id=f"approval-{tool_name}-{event.tool_use['toolUseId']}",
                name=f"{tool_name} Onayi",
                reason=f"Tool: {tool_name}\nParametreler: {event.tool_use.get('input', {})}",
            )
            raise InterruptException(interrupt)
```

---

## BOLUM 10: YAPILANDIRMA SISTEMI

### 10.1 Config Dosyasi

```yaml
# ~/.aethon/config.yaml

# Model yapilandirmasi
model:
  provider: ollama
  host: "http://localhost:11434"
  model_id: "qwen3-coder-next"
  temperature: 1.0
  top_p: 0.95
  top_k: 40

# Kanal yapilandirmasi
channels:
  whatsapp:
    enabled: false  # QR kod eslestirme sonrasi true yap
  telegram:
    enabled: true
    token: "${TELEGRAM_BOT_TOKEN}"  # Ortam degiskeninden
  discord:
    enabled: true
    token: "${DISCORD_BOT_TOKEN}"
  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
  webchat:
    enabled: true
    port: 18790
  cli:
    enabled: true

# Guvenlik
security:
  workspace_only: true                # Dosya erisimini workspace ile sinirla
  require_approval:                   # Onay gerektiren tool'lar
    - shell
    - file_write
    - send_message
  blocked_commands:                   # Yasakli shell komutlari
    - "rm -rf /"
    - "sudo"
    - "mkfs"

# Hafiza
memory:
  type: sqlite_vector
  db_path: "~/.aethon/memory.sqlite"

# Session
session:
  type: file
  base_dir: "~/.aethon/sessions"
  conversation_manager: summarizing
  max_messages: 50

# Is akislari (SOP'lar)
sops:
  enabled: true
  directories:
    - "~/.aethon/workspace/sops"
  auto_load: true

# Multi-agent
multi_agent:
  enabled: true
  specialists:
    - coder
    - researcher
    - analyst
    - planner
  default_mode: agent_as_tool  # "swarm", "graph", veya "agent_as_tool"
  max_handoffs: 10
  timeout: 300

# Zamanlayici
scheduler:
  enabled: true
  jobs:
    morning_brief:
      cron: "0 9 * * 1-5"  # Hafta ici sabah 9
      sop: morning-brief

# Yollar
paths:
  workspace: "~/.aethon/workspace"
  sessions: "~/.aethon/sessions"
  memory_db: "~/.aethon/memory.sqlite"
  logs: "~/.aethon/logs"
```

### 10.2 Dizin Yapisi

```
~/.aethon/
  ├── config.yaml               # Ana yapilandirma
  ├── workspace/
  │   ├── SOUL.md               # Agent kisiligi
  │   ├── TOOLS.md              # Kullanici tercihleri
  │   ├── CONTEXT.md            # Mevcut baglam (otomatik)
  │   └── sops/                 # SOP dosyalari
  │       ├── code-assist.sop.md
  │       ├── pdd.sop.md
  │       ├── morning-brief.sop.md
  │       └── ...
  ├── sessions/                 # Session verileri
  │   └── session_<id>/
  │       ├── agents/
  │       └── messages/
  ├── memory.sqlite             # Uzun vadeli hafiza
  ├── logs/                     # Islem kayitlari
  │   └── 2026-03-12.log
  └── credentials/              # Kanal token'lari (0600 izinler)
      ├── telegram.env
      ├── discord.env
      └── slack.env
```

---

## BOLUM 11: UYGULAMA YOL HARITASI

### Faz 1: Cekirdek (1-2 Hafta)

**Hedef:** CLI + WebChat + tek agent calisir halde

```
[ ] Proje iskeleti olustur (Python paketi, pyproject.toml)
[ ] AethonConfig sinifi (YAML yukleyici)
[ ] OllamaModel entegrasyonu (Qwen3-Coder-Next)
[ ] Temel Agent olusturma (system prompt, temel tool'lar)
[ ] CLI Adapter (prompt_toolkit)
[ ] WebChat Adapter (FastAPI + WebSocket)
[ ] Basit session yonetimi (FileSessionManager)
[ ] SecurityHookProvider (temel guvenlik)
[ ] SOUL.md ve TOOLS.md sistemi
[ ] `aethon start` komutu
```

**Sonuc:** Terminalden ve tarayicidan AETHON ile konusabilirsin.

### Faz 2: Kanallar + Hafiza (1-2 Hafta)

**Hedef:** Tum mesajlasma kanallari + kalici hafiza

```
[ ] ChannelAdapter base class
[ ] Telegram Adapter (aiogram)
[ ] Discord Adapter (discord.py)
[ ] Slack Adapter (slack-bolt)
[ ] WhatsApp Adapter (neonize veya bridge)
[ ] Message Router (session eslestirme)
[ ] Vektorel Hafiza (SQLite + Ollama embeddings)
[ ] Konusma Yonetimi (SummarizingConversationManager)
[ ] Kanal-arasi session izolasyonu
[ ] Media destegi (gorsel, dosya, ses)
```

**Sonuc:** WhatsApp, Telegram, Discord, Slack'ten AETHON'a mesaj gonderebilirsin.

### Faz 3: Multi-Agent + SOP (1-2 Hafta)

**Hedef:** Uzman takim + is akislari

```
[ ] Uzman agent tanimlari (Kodcu, Arastirmaci, Analist, Planlayici)
[ ] Agent-as-Tool deseni (ask_coder, ask_researcher, vb.)
[ ] Swarm entegrasyonu (isbirlikci gorevler)
[ ] Graph entegrasyonu (pipeline gorevler)
[ ] SOP yukleyici ve calistiricisi
[ ] Dahili SOP'lari entegre et (code-assist, PDD)
[ ] Ozel SOP yazma destegi
[ ] SOP tetikleme (slash command: /morning-brief)
[ ] Yapilandirilmis cikti entegrasyonu (Pydantic)
[ ] Interrupt mekanizmasi (insan onayi)
```

**Sonuc:** "Bu projeyi planla ve implement et" diyebilirsin — takim calismaya baslar.

### Faz 4: Cilalama + Ileri Ozellikler (Surekli)

**Hedef:** Uretim kalitesi, ileri ozellikler

```
[ ] Zamanlayici (cron-tabanli SOP tetikleme)
[ ] Webhook destegi (dis tetikleyiciler)
[ ] OpenTelemetry entegrasyonu (detayli gozlemlenebilirlik)
[ ] Web dashboard (session izleme, config duzenleme)
[ ] Ses destegi (Bidi streaming deneysel)
[ ] MCP sunucu entegrasyonu (dis tool kaynaklari)
[ ] Plugin sistemi (ucuncu taraf genisleme)
[ ] Otomatik context guncelleme (CONTEXT.md)
[ ] Performans optimizasyonu (caching, lazy loading)
[ ] Kapsamli test suite
```

---

## BOLUM 12: PROJE YAPISI

```
aethon/
  ├── pyproject.toml
  ├── README.md
  ├── aethon/
  │   ├── __init__.py
  │   ├── __main__.py          # CLI giris noktasi: python -m aethon
  │   ├── config.py            # AethonConfig (YAML yukleyici)
  │   │
  │   ├── gateway/
  │   │   ├── __init__.py
  │   │   ├── server.py        # AethonGateway (ana surec)
  │   │   └── router.py        # MessageRouter (session eslestirme)
  │   │
  │   ├── channels/
  │   │   ├── __init__.py
  │   │   ├── base.py          # ChannelAdapter, InboundMessage, OutboundMessage
  │   │   ├── cli.py           # CLIAdapter (prompt_toolkit)
  │   │   ├── webchat.py       # WebChatAdapter (FastAPI + WS)
  │   │   ├── telegram.py      # TelegramAdapter (aiogram)
  │   │   ├── discord.py       # DiscordAdapter (discord.py)
  │   │   ├── slack.py         # SlackAdapter (slack-bolt)
  │   │   └── whatsapp.py      # WhatsAppAdapter (neonize/bridge)
  │   │
  │   ├── agent/
  │   │   ├── __init__.py
  │   │   ├── runtime.py       # AethonRuntime (agent yasam dongusu)
  │   │   ├── prompt.py        # System prompt katmanlari
  │   │   ├── specialists.py   # Uzman agent tanimlari
  │   │   ├── teams.py         # TeamOrchestrator (Swarm/Graph)
  │   │   └── hooks/
  │   │       ├── __init__.py
  │   │       ├── security.py  # SecurityHookProvider
  │   │       ├── approval.py  # ApprovalHookProvider
  │   │       ├── telemetry.py # TelemetryHookProvider
  │   │       └── memory.py    # MemoryGuardHook
  │   │
  │   ├── tools/
  │   │   ├── __init__.py
  │   │   ├── messaging.py     # send_message, reply
  │   │   ├── delegate.py      # ask_coder, ask_researcher, ask_analyst
  │   │   ├── scheduler.py     # schedule_task
  │   │   └── memory_tool.py   # manage_memory
  │   │
  │   ├── memory/
  │   │   ├── __init__.py
  │   │   └── vector.py        # VectorMemory (SQLite + embedding)
  │   │
  │   ├── session/
  │   │   ├── __init__.py
  │   │   └── manager.py       # AethonSessionManager
  │   │
  │   ├── sops/
  │   │   ├── __init__.py
  │   │   └── runner.py        # SOP yukleyici ve calistiricisi
  │   │
  │   └── ui/
  │       └── dist/            # WebChat frontend (statik dosyalar)
  │
  ├── workspace/               # Varsayilan workspace sablonu
  │   ├── SOUL.md
  │   ├── TOOLS.md
  │   ├── CONTEXT.md
  │   └── sops/
  │       ├── code-assist.sop.md
  │       └── morning-brief.sop.md
  │
  └── tests/
      ├── test_gateway.py
      ├── test_router.py
      ├── test_agents.py
      └── test_memory.py
```

---

## BOLUM 13: BAGIMLILIKLAR

```toml
# pyproject.toml

[project]
name = "aethon"
version = "0.1.0"
requires-python = ">=3.10"

dependencies = [
    # Cekirdek
    "strands-agents>=1.0.0",
    "strands-agents-tools>=0.1.0",
    "strands-agents-sops>=0.1.0",

    # Gateway
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "websockets>=12.0",
    "aiohttp>=3.9.0",

    # Kanal Adapterleri
    "aiogram>=3.0.0",           # Telegram
    "discord.py>=2.0.0",        # Discord
    "slack-bolt>=1.18.0",       # Slack

    # Hafiza
    "aiosqlite>=0.19.0",

    # Config
    "pyyaml>=6.0",
    "pydantic>=2.4.0",

    # CLI
    "prompt_toolkit>=3.0.0",
    "rich>=14.0.0",
    "click>=8.0.0",

    # Zamanlayici
    "apscheduler>=3.10.0",
]

[project.optional-dependencies]
whatsapp = ["neonize>=1.0.0"]    # WhatsApp destegi
voice = ["elevenlabs>=1.0.0"]     # Ses destegi
```

---

## BOLUM 14: HIZLI BASLANGIC (KULLANICI PERSPEKTIFI)

AETHON tamamen kuruldugunda kullanici deneyimi:

```bash
# 1. Kur
pip install aethon

# 2. Baslat (ilk seferde sihirbaz calisir)
aethon start

# Sihirbaz:
# → Ollama model secimi (qwen3-coder-next)
# → Kanal yapilandirmasi (Telegram token, Discord token, vb.)
# → Workspace olusturma (~/.aethon/workspace/)
# → SOUL.md kisilik ayari

# 3. Kullan
# CLI'dan:
aethon chat
> Merhaba, bugun ne yapacagiz?

# Telegram'dan:
@aethon_bot Bu projedeki hatalari bul ve duzelt

# Discord'dan:
!aethon /code-assist task=implement-login-page

# WebChat'ten:
# http://127.0.0.1:18790/ui adresini ac
```

---

## SONUC

AETHON, OpenClaw'un en iyi fikirlerini alip Strands Agents SDK'nin gucuyle birlestiren, guvenlik-oncelikli, Python-native, coklu-agent destekli bir kisisel AI asistan sistemidir.

**OpenClaw'u asan noktalar:**
1. **Multi-agent takim** — tek agent yerine uzman takim
2. **SOP is akislari** — tekrarlanabilir, yapilandirilmis gorevler
3. **Yapilandirilmis cikti** — Pydantic ile dogrulanmis sonuclar
4. **Guvenlik-oncelikli** — bilinen tum OpenClaw aciklari giderilmis
5. **Python ekosistemi** — ML/AI kutuphaneleri ile dogal uyum
6. **70+ tool** — Pi'nin 4 tool'una karsi devasa tool ekosistemi
7. **OpenTelemetry** — dahili gozlemlenebilirlik
8. **Interrupt mekanizmasi** — gercek human-in-the-loop

Bu dokuman, AETHON'un tasarim planidir. Artik kodlamaya baslayabiliriz.
