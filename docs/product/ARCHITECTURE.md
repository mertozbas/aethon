# AETHON — Teknik Mimari Dokumani

> Versiyon: 0.1.0 | Tarih: 2026-03-12
> Bu dokuman AETHON'un teknik mimarisini, veri akislarini ve bilesken iliskilerini detayli olarak tanimlar.

---

## 1. Yuksek Seviye Mimari

```
╔══════════════════════════════════════════════════════════════════════╗
║                          AETHON SISTEMI                             ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌───────────────────────────────────────────────────────────────┐  ║
║  │                      GATEWAY KATMANI                           │  ║
║  │              (Python asyncio + aiohttp)                        │  ║
║  │                                                                │  ║
║  │  ┌──────┐ ┌──────┐ ┌───────┐ ┌─────┐ ┌───────┐ ┌─────┐     │  ║
║  │  │Whats │ │Tele  │ │Discord│ │Slack│ │WebChat│ │ CLI │       │  ║
║  │  │App   │ │gram  │ │       │ │     │ │       │ │     │       │  ║
║  │  └──┬───┘ └──┬───┘ └──┬────┘ └──┬──┘ └──┬────┘ └──┬──┘     │  ║
║  │     └────────┴────────┴───┬─────┴───────┴─────────┘          │  ║
║  └───────────────────────────┼───────────────────────────────────┘  ║
║                              │                                       ║
║                    ┌─────────▼─────────┐                            ║
║                    │  MESSAGE ROUTER    │                            ║
║                    │ (Session Resolver  │                            ║
║                    │  + Auth + Queue)   │                            ║
║                    └─────────┬─────────┘                            ║
║                              │                                       ║
║  ┌───────────────────────────▼───────────────────────────────────┐  ║
║  │                     AGENT KATMANI                               │  ║
║  │                                                                  │  ║
║  │  ┌────────────────────────────────────────────────────────┐    │  ║
║  │  │              AETHON RUNTIME                              │   │  ║
║  │  │                                                          │   │  ║
║  │  │   System Prompt       ┌───────────────────┐             │   │  ║
║  │  │   Composer      ────▶ │  STRANDS AGENT    │             │   │  ║
║  │  │                       │  (OllamaModel)    │             │   │  ║
║  │  │   Hook Pipeline ────▶ │                   │             │   │  ║
║  │  │                       │   ┌─────────────┐ │             │   │  ║
║  │  │   Tool Registry ────▶ │   │ Tool Loop   │ │             │   │  ║
║  │  │                       │   │ Model→Tool  │ │             │   │  ║
║  │  │                       │   │ →Model→...  │ │             │   │  ║
║  │  │                       │   └─────────────┘ │             │   │  ║
║  │  │                       └───────────────────┘             │   │  ║
║  │  └────────────────────────────────────────────────────────┘    │  ║
║  │                              │                                   │  ║
║  │         ┌────────────────────┼────────────────────┐             │  ║
║  │         │                    │                    │              │  ║
║  │    ┌────▼─────┐      ┌──────▼──────┐     ┌──────▼──────┐      │  ║
║  │    │ Kodcu    │      │ Arastirmaci │     │  Analist    │       │  ║
║  │    │ Agent    │      │ Agent       │     │  Agent      │       │  ║
║  │    └──────────┘      └─────────────┘     └─────────────┘       │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                              │                                       ║
║  ┌───────────────────────────▼───────────────────────────────────┐  ║
║  │                    ALTYAPI KATMANI                               │  ║
║  │                                                                  │  ║
║  │  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌──────────────────┐  │  ║
║  │  │ Vektor   │ │ File       │ │ YAML   │ │ OllamaModel     │  │  ║
║  │  │ Hafiza   │ │ Session    │ │ Config │ │ (LLM Provider)  │  │  ║
║  │  │ (SQLite) │ │ Manager    │ │        │ │                  │  │  ║
║  │  └──────────┘ └────────────┘ └────────┘ └──────────────────┘  │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 2. Katman Detaylari

### 2.1 Gateway Katmani

**Sorumluluk:** Dis dunyadan gelen mesajlari almak, normalize etmek ve agent katmanina iletmek. Agent'in yanitlarini uygun kanala geri gondermek.

**Bileskenler:**

| Bilesken | Sinif | Dosya |
|----------|-------|-------|
| Gateway Sunucu | `AethonGateway` | `aethon/gateway/server.py` |
| Message Router | `MessageRouter` | `aethon/gateway/router.py` |
| Base Adapter | `ChannelAdapter` (ABC) | `aethon/channels/base.py` |
| CLI Adapter | `CLIAdapter` | `aethon/channels/cli.py` |
| WebChat Adapter | `WebChatAdapter` | `aethon/channels/webchat.py` |
| Telegram Adapter | `TelegramAdapter` | `aethon/channels/telegram.py` |
| Discord Adapter | `DiscordAdapter` | `aethon/channels/discord_adapter.py` |
| Slack Adapter | `SlackAdapter` | `aethon/channels/slack_adapter.py` |
| WhatsApp Adapter | `WhatsAppAdapter` | `aethon/channels/whatsapp.py` |

**Mesaj Modelleri:**

```python
@dataclass
class InboundMessage:
    channel: str               # "cli", "webchat", "telegram", ...
    sender_id: str             # Kanal-spesifik kullanici ID
    sender_name: str           # Goruntulenen isim
    text: str                  # Mesaj metni
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: str | None = None
    thread_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw: dict = field(default_factory=dict)

@dataclass
class OutboundMessage:
    channel: str
    recipient_id: str
    text: str
    media: list[MediaAttachment] = field(default_factory=list)
    reply_to: str | None = None
    thread_id: str | None = None

@dataclass
class MediaAttachment:
    type: str                  # "image", "audio", "video", "document"
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None
```

### 2.2 Message Router

**Sorumluluk:** Gelen mesaji session'a esle, kimlik dogrula, agent runtime'a ilet.

```
InboundMessage
     │
     ▼
┌─────────────┐
│ Auth Check   │──▶ Allowlist kontrolu (tek kullanici, sender_id dogrulama)
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ Session      │──▶ channel:sender_id → session_id eslestirmesi
│ Resolver     │    Thread varsa: channel:thread_id
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Agent        │──▶ AethonRuntime.process(message, session_id)
│ Dispatch     │
└──────┬───────┘
       │
       ▼
OutboundMessage
```

**Session ID Stratejisi:**
```
Ana konusma:  "main"
Kanal DM:     "{channel}:{sender_id}"    → "telegram:12345678"
Thread:       "{channel}:{thread_id}"     → "discord:thread_98765"
```

### 2.3 Agent Katmani

**Sorumluluk:** LLM etkilesimi, tool calistirma, multi-agent orkestrasyon.

**Ana Siniflar:**

| Sinif | Sorumluluk |
|-------|-----------|
| `AethonRuntime` | Agent yasam dongusu yonetimi |
| `SystemPromptComposer` | Katmanli system prompt olusturma |
| `SpecialistFactory` | Uzman agent olusturma |
| `TeamOrchestrator` | Multi-agent koordinasyonu |
| `SOPRunner` | SOP yukleme ve calistirma |

**Strands Agent Entegrasyonu (Dogrulanmis API):**

```python
from strands import Agent
from strands.models import Model
from strands.session import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from aethon.agent.model_factory import create_model

# Model olusturma — config'deki provider'a gore otomatik
# provider: "ollama" → OllamaModel
# provider: "openai" → OpenAIModel
# provider: "anthropic" → AnthropicModel
# provider: "bedrock" → BedrockModel
# provider: "gemini" → GeminiModel
# ... vb.
model = create_model(config.model)

# Session manager — her session icin ayri instance
session_mgr = FileSessionManager(
    session_id="telegram:12345678",
    storage_dir="~/.aethon/sessions"
)

# Conversation manager — context penceresi yonetimi
conv_mgr = SummarizingConversationManager(
    summary_ratio=0.3,              # Mesajlarin %30'unu ozetle
    preserve_recent_messages=10,     # Son 10 mesaji koru
)

# Agent olusturma
agent = Agent(
    model=model,
    system_prompt=composed_prompt,
    tools=[file_read, file_write, editor, shell, ...],
    session_manager=session_mgr,
    conversation_manager=conv_mgr,
    hooks=[SecurityHookProvider(), TelemetryHookProvider()],
    agent_id="main",
    name="AETHON",
)

# Senkron cagri
result = agent("Merhaba, bugun ne yapacagiz?")
# result.message → Son yanit mesaji
# result.metrics → Token kullanimi, sure, vb.
```

### 2.4 Altyapi Katmani

**Sorumluluk:** Veri kaliciligi, yapilandirma, model erisimi.

| Bilesken | Teknoloji | Aciklama |
|----------|-----------|----------|
| Vektor Hafiza | SQLite + Ollama `/api/embed` | Uzun vadeli semantik hafiza (LRU embedding cache) |
| Session | FileSessionManager | Konusma gecmisi (LRU session cache) |
| Config | PyYAML + Pydantic | `~/.aethon/config.yaml` |
| Model | **Multi-Provider Factory** | Ollama, OpenAI, Anthropic, Bedrock, Gemini, LiteLLM, Mistral |
| Zamanlayici | APScheduler | Cron-tabanli SOP tetikleme |
| Telemetri | TelemetryHookProvider | Tool/model metrik toplama (deque) |
| Dashboard | FastAPI + Vanilla JS | Web izleme paneli + WebSocket stream |
| Webhook | FastAPI | HTTP webhook endpoint'leri |
| MCP | strands MCPClient | Harici MCP sunucu entegrasyonu |

---

## 3. Veri Akisi (Uctan Uca)

```
1. Kullanici Telegram'dan mesaj gonderir: "Bu projedeki hatalari bul"
   │
2. TelegramAdapter mesaji alir, normalize eder:
   │  → InboundMessage(channel="telegram", sender_id="12345678",
   │                    sender_name="Mert", text="Bu projedeki hatalari bul")
   │
3. MessageRouter:
   │  a. Auth: sender_id allowlist'te mi? → EVET
   │  b. Session: "telegram:12345678" → session_id
   │  c. Runtime'a ilet
   │
4. AethonRuntime:
   │  a. FileSessionManager'dan konusma gecmisini yukle
   │  b. SystemPromptComposer: SOUL.md + TOOLS.md + CONTEXT.md + SOP listesi
   │  c. Agent olustur/getir
   │  d. agent("Bu projedeki hatalari bul")
   │
5. Strands Agent Event Loop:
   │  a. Model cagrisi → Qwen3-Coder-Next
   │  b. Model karar verir: ask_coder tool'unu cagir
   │  c. BeforeToolCallEvent hook → SecurityHookProvider kontrol
   │  d. Tool calisir: Kodcu Agent devreye girer
   │  e. Kodcu Agent kendi tool loop'unu calistirir (shell, editor, vb.)
   │  f. AfterToolCallEvent hook → Sonuc loglanir
   │  g. Model tekrar cagirilir → son yaniti uretir
   │  h. end_turn
   │
6. AethonRuntime:
   │  a. Session'a kaydet
   │  b. Uzun vadeli hafizaya kaydet (gerekirse)
   │  c. OutboundMessage olustur
   │
7. MessageRouter → TelegramAdapter:
   │  → OutboundMessage(channel="telegram", recipient_id="12345678",
   │                     text="3 hata bulundu ve duzeltildi: ...")
   │
8. TelegramAdapter → Kullaniciya Telegram mesaji gonderilir
```

---

## 4. System Prompt Mimari

AETHON'un system prompt'u katmanli olarak birlestilir:

```
┌─────────────────────────────────────┐
│ Katman 1: SOUL.md                   │
│ → Agent kisiligi ve davranis        │
│   kurallari                         │
├─────────────────────────────────────┤
│ Katman 2: TOOLS.md                  │
│ → Kullanici tercihleri,             │
│   konvansiyonlar                    │
├─────────────────────────────────────┤
│ Katman 3: CONTEXT.md                │
│ → Mevcut proje/is baglami          │
│   (otomatik guncellenir)           │
├─────────────────────────────────────┤
│ Katman 4: SOP Listesi               │
│ → Kullanilabilir SOP komutlari     │
│   (sadece isim + aciklama)         │
├─────────────────────────────────────┤
│ Katman 5: Kanal Bilgisi             │
│ → Aktif session ID, kanal adi      │
├─────────────────────────────────────┤
│ Katman 6: Zaman                     │
│ → datetime.now().isoformat()        │
└─────────────────────────────────────┘
```

**Dosya Konumlari:**
```
~/.aethon/workspace/
  ├── SOUL.md        → Kisilik (manuel duzenlenir)
  ├── TOOLS.md       → Tercihler (manuel duzenlenir)
  ├── CONTEXT.md     → Baglam (otomatik + manuel)
  └── sops/          → SOP dosyalari
```

---

## 5. Tool Pipeline

### 5.1 Tool Kategorileri

**Strands Dahili Tool'lar (strands-agents-tools):**

| Kategori | Tool'lar | Import |
|----------|---------|--------|
| Dosya | `file_read`, `file_write`, `editor` | `from strands_tools import file_read` |
| Shell | `shell`, `python_repl` | `from strands_tools import shell` |
| Web | `http_request` | `from strands_tools import http_request` |
| Matematik | `calculator` | `from strands_tools import calculator` |
| Dusunme | `think` | `from strands_tools import think` |
| Zaman | `current_time` | `from strands_tools import current_time` |
| Hafiza | `memory`, `mem0_memory` | `from strands_tools import memory` |

**AETHON Ozel Tool'lar:**

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `ask_coder` | `aethon/tools/delegate.py` | Kodlama gorevini kodcu agent'a devret |
| `ask_researcher` | `aethon/tools/delegate.py` | Arastirma gorevini arastirmaciya devret |
| `ask_analyst` | `aethon/tools/delegate.py` | Analiz gorevini analiste devret |
| `ask_planner` | `aethon/tools/delegate.py` | Planlama gorevini planlayiciya devret |
| `manage_memory` | `aethon/tools/memory_tool.py` | Uzun vadeli hafizayi yonet |
| `update_context` | `aethon/tools/context_tool.py` | CONTEXT.md baglamini yonet |
| `send_message` | `aethon/tools/messaging.py` | Baska kanala mesaj gonder |
| `schedule_task` | `aethon/tools/scheduler.py` | Cron tabanli gorev zamanla |
| `list_scheduled_jobs` | `aethon/tools/scheduler.py` | Zamanlanmis gorevleri listele |
| `remove_scheduled_job` | `aethon/tools/scheduler.py` | Zamanlanmis gorevi kaldir |

### 5.2 Tool Tanimlama Deseni

```python
from strands import tool

@tool
def ask_coder(task: str) -> str:
    """Kodlama gorevini kodcu uzmanina devret.

    Args:
        task: Kodlama gorevi aciklamasi
    """
    coder = get_specialist("coder")
    result = coder(task)
    return result.message["content"][0]["text"]
```

### 5.3 Hook Pipeline

Her tool cagrisi su pipeline'dan gecer:

```
Model "tool_use" uretir
        │
        ▼
┌────────────────────┐
│ BeforeToolCallEvent │
│                     │
│ 1. SecurityHook:    │  Tehlikeli komut + workspace kontrol
│    - Blocked cmds   │
│    - Workspace check│
│                     │
│ 2. MemoryGuardHook: │  Hassas bilgi korumasi
│    - API key/pass   │  (sadece manage_memory store'u)
│    - Token/SSH/PEM  │
│    - Kredi karti    │
│                     │
│ 3. TelemetryHook:   │  Zamanlama baslat
│    - Timer baslat   │
│                     │
│ 4. ApprovalHook:    │  Kullanici onayi
│    - Interrupt?     │
└────────┬────────────┘
         │
         ▼
┌───────────────────┐
│   TOOL CALISIR    │
└────────┬──────────┘
         │
         ▼
┌────────────────────┐
│ AfterToolCallEvent  │
│                     │
│ TelemetryHook:      │
│  - Timer durdur     │
│  - Metrik logla     │
│  - Hata takibi      │
└─────────────────────┘
```

**Hook Sirasi:** Security → MemoryGuard → Telemetry → Approval. Security tehlikeli operasyonlari engeller, MemoryGuard hassas veriyi korur, Telemetry gecen her seyi kaydeder, Approval son kullanici onayini ister.

---

## 6. Multi-Agent Mimarisi

### 6.1 Agent-as-Tool (Varsayilan Mod)

```
Kullanici mesaji
       │
       ▼
┌──────────────────┐
│  ORCHESTRATOR    │  System Prompt: "Sen ana yonlendiricisin.
│  (Ana Agent)     │  Gorevleri uzman agent'lara devret."
│                  │
│  Tools:          │
│  - ask_coder     │──▶ Kodcu Agent (bagimsiz Strands Agent)
│  - ask_researcher│──▶ Arastirmaci Agent
│  - ask_analyst   │──▶ Analist Agent
│  - file_read     │
│  - shell         │
│  - think         │
└──────────────────┘
```

Model, hangi uzmanin gerektigine kendisi karar verir. Orchestrator basit gorevleri kendisi yapar, karmasik gorevleri devreder.

### 6.2 Swarm (Isbirligi Modu)

```python
from strands.multiagent import Swarm

swarm = Swarm(
    nodes=[orchestrator, coder, researcher, analyst],
    entry_point=orchestrator,
    max_handoffs=10,
    max_iterations=10,
    execution_timeout=300.0,
    node_timeout=120.0,
)

result = swarm("Bu projeyi planla ve implement et")
# result.final_response → Son yanit
# result.node_history → Hangi agent'lar calisti
```

Agent'lar birbirine handoff yapar. Orchestrator gorevi planlayiciya, planlayici kodcuya, vb. devreder.

### 6.3 Graph (Pipeline Modu)

```python
from strands.multiagent import GraphBuilder

builder = GraphBuilder()
plan_node = builder.add_node(planner, "planlama")
research_node = builder.add_node(researcher, "arastirma")
code_node = builder.add_node(coder, "kodlama")

builder.add_edge(plan_node, research_node)
builder.add_edge(research_node, code_node)
builder.set_entry_point("planlama")

graph = builder.build()
result = graph("Yeni API endpoint implement et")
```

Deterministik sirada calisir: Planlama → Arastirma → Kodlama

---

## 7. Hafiza Mimarisi

### 7.1 Uc Katmanli Hafiza

```
┌─────────────────────────────────────────┐
│           UZUN VADELI HAFIZA            │
│     (SQLite + Ollama Embeddings)        │
│                                         │
│  Kullanici tercihleri, bilgiler,        │
│  ogrenilen kaliplar                     │
│  → Aylar/yillar boyunca kalir           │
│  → Semantik arama ile erisilir          │
├─────────────────────────────────────────┤
│           SESSION HAFIZA                │
│       (FileSessionManager)              │
│                                         │
│  Konusma gecmisi, agent state           │
│  → Session boyunca kalir                │
│  → JSON dosyalari olarak saklanir       │
│                                         │
│  Dizin:                                 │
│  sessions/session_{id}/                 │
│    ├── session.json                     │
│    └── agents/agent_{id}/              │
│        ├── agent.json                   │
│        └── messages/message_{n}.json    │
├─────────────────────────────────────────┤
│          CALISMA HAFIZA                 │
│   (SummarizingConversationManager)      │
│                                         │
│  Son 10 mesaj + onceki mesajlarin       │
│  ozeti                                  │
│  → Her model cagrisinda yenilenir       │
│  → Context window'a sigar              │
└─────────────────────────────────────────┘
```

### 7.2 Vektor Hafiza Detayi

```
SQLite Tablo: memories
┌────────┬─────────┬───────────┬──────────┬───────────┬────────────┐
│ id     │ content │ category  │ embedding│ metadata  │ created_at │
│ INTEGER│ TEXT    │ TEXT      │ TEXT     │ TEXT      │ TEXT       │
│ PK     │         │           │ JSON     │ JSON      │ ISO 8601   │
└────────┴─────────┴───────────┴──────────┴───────────┴────────────┘

Embedding: Ollama /api/embed endpoint'i
Arama: Cosine similarity (Python tarafinda hesaplanir)
```

---

## 8. Yapilandirma Mimarisi

### 8.1 Config Hiyerarsisi

```
1. Varsayilan degerler (Python kodu)
   │
2. ~/.aethon/config.yaml (kullanici yapilandirmasi)
   │
3. Ortam degiskenleri (${TELEGRAM_BOT_TOKEN})
   │
4. CLI argumanlar (--port 8080)
```

### 8.2 Config Modeli (Pydantic)

```python
class ModelConfig(BaseModel):
    provider: str = "ollama"
    host: str = "http://localhost:11434"
    model_id: str = "qwen3-coder-next"
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40

class ChannelConfig(BaseModel):
    enabled: bool = False
    # Kanal-spesifik alanlar alt sinifta

class SecurityConfig(BaseModel):
    workspace_only: bool = True
    require_approval: list[str] = ["shell", "file_write", "send_message"]
    blocked_commands: list[str] = ["rm -rf /", "sudo", "mkfs"]

class AethonConfig(BaseModel):
    model: ModelConfig
    channels: ChannelsConfig
    security: SecurityConfig
    memory: MemoryConfig
    session: SessionConfig
    sops: SOPConfig
    multi_agent: MultiAgentConfig
    telemetry: TelemetryConfig       # Metrik toplama
    memory_guard: MemoryGuardConfig  # Hassas bilgi korumasi
    scheduler: SchedulerConfig       # Cron-tabanli SOP zamanlama
    dashboard: DashboardConfig       # Web izleme paneli
    webhook: WebhookConfig           # HTTP webhook desteği
    mcp: MCPConfig                   # MCP sunucu entegrasyonu
    performance: PerformanceConfig   # LRU cache + model warm-up
    paths: PathsConfig
```

---

## 9. Dizin Yapisi

```
~/.aethon/                              # Kullanici veri dizini
  ├── config.yaml                       # Ana yapilandirma
  ├── workspace/                        # Agent calisma alani
  │   ├── SOUL.md                       # Kisilik
  │   ├── TOOLS.md                      # Tercihler
  │   ├── CONTEXT.md                    # Baglam
  │   └── sops/                         # SOP dosyalari
  ├── sessions/                         # Session verileri
  │   └── session_{id}/
  │       ├── session.json
  │       └── agents/
  ├── memory.sqlite                     # Uzun vadeli hafiza
  ├── logs/                             # Log dosyalari
  └── credentials/                      # Token'lar (0600)

aethon/                                  # Proje kaynak kodu
  ├── pyproject.toml
  ├── aethon/
  │   ├── __init__.py
  │   ├── __main__.py                   # python -m aethon
  │   ├── config.py                     # AethonConfig (17 config modeli)
  │   ├── gateway/
  │   │   ├── server.py                 # AethonGateway (lifecycle yonetimi)
  │   │   ├── router.py                # MessageRouter (session + auth)
  │   │   └── webhooks.py             # Webhook endpoint'leri
  │   ├── channels/
  │   │   ├── base.py                   # ChannelAdapter, InboundMessage, OutboundMessage
  │   │   ├── cli.py                    # CLIAdapter
  │   │   ├── webchat.py               # WebChatAdapter (FastAPI + WS)
  │   │   ├── telegram.py              # TelegramAdapter
  │   │   ├── discord_adapter.py       # DiscordAdapter
  │   │   ├── slack_adapter.py         # SlackAdapter
  │   │   └── whatsapp.py             # WhatsAppAdapter
  │   ├── agent/
  │   │   ├── runtime.py               # AethonRuntime (LRU cache + warm-up)
  │   │   ├── model_factory.py         # Multi-provider model factory
  │   │   ├── prompt.py                # SystemPromptComposer
  │   │   ├── specialists.py           # SpecialistFactory
  │   │   ├── teams.py                 # TeamOrchestrator
  │   │   ├── context_updater.py       # CONTEXT.md otomatik guncelleme
  │   │   └── hooks/
  │   │       ├── security.py          # SecurityHookProvider
  │   │       ├── approval.py          # ApprovalHookProvider
  │   │       ├── telemetry.py         # TelemetryHookProvider
  │   │       └── memory_guard.py      # MemoryGuardHookProvider
  │   ├── tools/
  │   │   ├── delegate.py              # ask_coder, ask_researcher, ask_analyst, ask_planner
  │   │   ├── memory_tool.py           # manage_memory
  │   │   ├── context_tool.py          # update_context
  │   │   ├── messaging.py             # send_message
  │   │   ├── scheduler.py             # schedule_task, list/remove jobs
  │   │   └── mcp_integration.py       # MCPToolLoader
  │   ├── memory/
  │   │   └── vector.py                # VectorMemory (embedding LRU cache)
  │   ├── sops/
  │   │   ├── runner.py                # SOPRunner
  │   │   └── builtin/                 # Dahili SOP dosyalari
  │   └── ui/
  │       ├── __init__.py
  │       └── dashboard.py             # Web dashboard + API endpoint'leri
  ├── workspace/                        # Varsayilan workspace sablonu
  │   ├── SOUL.md
  │   ├── TOOLS.md
  │   ├── CONTEXT.md
  │   └── sops/
  └── tests/                            # 294 test
```

---

## 10. Bagimlilik Grafigi

```
aethon
  ├── strands-agents           # Agent framework (cekirdek)
  │   └── strands-agents-tools # 47+ tool
  │   └── strands-agents-sops  # SOP sistemi
  │
  ├── fastapi + uvicorn        # WebChat + Dashboard + Webhook + API
  │   └── websockets           # WS destegi (chat + telemetri)
  │
  ├── aiogram                  # Telegram
  ├── discord.py               # Discord
  ├── slack-bolt               # Slack
  ├── neonize (optional)       # WhatsApp
  │
  ├── prompt_toolkit + rich    # CLI
  ├── click                    # CLI komutlari
  │
  ├── pyyaml + pydantic        # Config
  ├── aiosqlite                # Veritabani
  ├── apscheduler              # Zamanlayici
  └── mcp (optional)           # MCP sunucu entegrasyonu
```

---

## 11. Port ve Endpoint Haritasi

| Servis | Port | Endpoint | Protokol |
|--------|------|----------|----------|
| Ollama | 11434 | `/api/chat`, `/api/embed` | HTTP |
| WebChat | 18790 | `/ws/chat` | WebSocket |
| WebChat UI | 18790 | `/ui` | HTTP (statik) |
| Dashboard | 18790 | `/dashboard` | HTTP |
| Dashboard API | 18790 | `/api/sessions`, `/api/memory`, `/api/config`, `/api/telemetry`, `/api/scheduler/jobs` | HTTP REST |
| Hafiza Arama | 18790 | `/api/memory/search` | HTTP POST |
| Telemetri Stream | 18790 | `/ws/telemetry` | WebSocket |
| Webhook (Kanal) | 18790 | `/webhook/{channel}` | HTTP POST |
| Webhook (Tetik) | 18790 | `/webhook/trigger` | HTTP POST |
| Telegram | - | Bot API polling | HTTPS (outbound) |
| Discord | - | Gateway WebSocket | WSS (outbound) |
| Slack | - | Socket Mode | WSS (outbound) |

**Onemli:** Tum yerelde dinleyen servisler `127.0.0.1` adresine baglidir. `0.0.0.0` KULLANILMAZ.

---

## 12. Performans Optimizasyonlari

### 12.1 Session LRU Cache

```
Runtime.agents: OrderedDict (LRU cache)

Erisim:                          Tasma:
┌───────────┐ move_to_end()     ┌───────────┐ popitem(last=False)
│ session_A │ ──────────────▶   │ en_eski   │ ──────────────▶ Disk'e kaydet
│ session_B │                   │ session_B │
│ session_C │                   │ session_C │
└───────────┘                   │ session_A │
                                └───────────┘
```

Varsayilan boyut: 10 session. Evict edilen session'lar disk'te kalir (FileSessionManager), tekrar erisince yuklenir.

### 12.2 Embedding LRU Cache

Tekrarlayan hafiza sorgulari icin `lru_cache` ile embedding sonuclari onbelleklenir. Varsayilan boyut: 100 embedding.

### 12.3 Model Warm-up

Baslangiçta dummy "Merhaba" istegi gondererek ilk kullanici mesajindaki gecikmeyi azaltir.
