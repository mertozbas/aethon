# AETHON — Technical Architecture Document

> Version: 0.1.0 | Date: 2026-03-12
> This document describes AETHON's technical architecture, data flows, and component relationships in detail.

---

## 1. High-Level Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                          AETHON SYSTEM                               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌───────────────────────────────────────────────────────────────┐  ║
║  │                      GATEWAY LAYER                              │  ║
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
║  │                     AGENT LAYER                                  │  ║
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
║  │    │ Coder    │      │ Researcher  │     │  Analyst    │       │  ║
║  │    │ Agent    │      │ Agent       │     │  Agent      │       │  ║
║  │    └──────────┘      └─────────────┘     └─────────────┘       │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                              │                                       ║
║  ┌───────────────────────────▼───────────────────────────────────┐  ║
║  │                    INFRASTRUCTURE LAYER                          │  ║
║  │                                                                  │  ║
║  │  ┌──────────┐ ┌────────────┐ ┌────────┐ ┌──────────────────┐  │  ║
║  │  │ Vector   │ │ File       │ │ YAML   │ │ OllamaModel     │  │  ║
║  │  │ Memory   │ │ Session    │ │ Config │ │ (LLM Provider)  │  │  ║
║  │  │ (SQLite) │ │ Manager    │ │        │ │                  │  │  ║
║  │  └──────────┘ └────────────┘ └────────┘ └──────────────────┘  │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 2. Layer Details

### 2.1 Gateway Layer

**Responsibility:** Receive messages from the outside world, normalize them, and forward them to the agent layer. Send the agent's responses back to the appropriate channel.

**Components:**

| Component | Class | File |
|-----------|-------|------|
| Gateway Server | `AethonGateway` | `aethon/gateway/server.py` |
| Message Router | `MessageRouter` | `aethon/gateway/router.py` |
| Base Adapter | `ChannelAdapter` (ABC) | `aethon/channels/base.py` |
| CLI Adapter | `CLIAdapter` | `aethon/channels/cli.py` |
| WebChat Adapter | `WebChatAdapter` | `aethon/channels/webchat.py` |
| Telegram Adapter | `TelegramAdapter` | `aethon/channels/telegram.py` |
| Discord Adapter | `DiscordAdapter` | `aethon/channels/discord_adapter.py` |
| Slack Adapter | `SlackAdapter` | `aethon/channels/slack_adapter.py` |
| WhatsApp Adapter | `WhatsAppAdapter` | `aethon/channels/whatsapp.py` |

**Message Models:**

```python
@dataclass
class InboundMessage:
    channel: str               # "cli", "webchat", "telegram", ...
    sender_id: str             # Channel-specific user ID
    sender_name: str           # Display name
    text: str                  # Message text
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

**Responsibility:** Map the incoming message to a session, verify identity, and forward to the agent runtime.

```
InboundMessage
     │
     ▼
┌─────────────┐
│ Auth Check   │──▶ Allowlist check (single user, sender_id verification)
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ Session      │──▶ channel:sender_id → session_id mapping
│ Resolver     │    If thread exists: channel:thread_id
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

**Session ID Strategy:**
```
Main conversation:  "main"
Channel DM:        "{channel}:{sender_id}"    → "telegram:12345678"
Thread:            "{channel}:{thread_id}"     → "discord:thread_98765"
```

### 2.3 Agent Layer

**Responsibility:** LLM interaction, tool execution, multi-agent orchestration.

**Main Classes:**

| Class | Responsibility |
|-------|----------------|
| `AethonRuntime` | Agent lifecycle management |
| `SystemPromptComposer` | Layered system prompt composition |
| `SpecialistFactory` | Specialist agent creation |
| `TeamOrchestrator` | Multi-agent coordination |
| `SOPRunner` | SOP loading and execution |

**Strands Agent Integration (Verified API):**

```python
from strands import Agent
from strands.models import Model
from strands.session import FileSessionManager
from strands.agent.conversation_manager import SummarizingConversationManager
from aethon.agent.model_factory import create_model

# Model creation — automatic based on provider in config
# provider: "ollama" → OllamaModel
# provider: "openai" → OpenAIModel
# provider: "anthropic" → AnthropicModel
# provider: "bedrock" → BedrockModel
# provider: "gemini" → GeminiModel
# ... etc.
model = create_model(config.model)

# Session manager — separate instance for each session
session_mgr = FileSessionManager(
    session_id="telegram:12345678",
    storage_dir="~/.aethon/sessions"
)

# Conversation manager — context window management
conv_mgr = SummarizingConversationManager(
    summary_ratio=0.3,              # Summarize 30% of messages
    preserve_recent_messages=10,     # Preserve last 10 messages
)

# Agent creation
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

# Synchronous call
result = agent("Merhaba, bugun ne yapacagiz?")
# result.message → Last response message
# result.metrics → Token usage, duration, etc.
```

### 2.4 Infrastructure Layer

**Responsibility:** Data persistence, configuration, model access.

| Component | Technology | Description |
|-----------|------------|-------------|
| Vector Memory | SQLite + Ollama `/api/embed` | Long-term semantic memory (LRU embedding cache) |
| Session | FileSessionManager | Conversation history (LRU session cache) |
| Config | PyYAML + Pydantic | `~/.aethon/config.yaml` |
| Model | **Multi-Provider Factory** | Ollama, OpenAI, Anthropic, Bedrock, Gemini, LiteLLM, Mistral |
| Scheduler | APScheduler | Cron-based SOP triggering |
| Telemetry | TelemetryHookProvider | Tool/model metric collection (deque) |
| Dashboard | FastAPI + Vanilla JS | Web monitoring panel + WebSocket stream |
| Webhook | FastAPI | HTTP webhook endpoints |
| MCP | strands MCPClient | External MCP server integration |

---

## 3. Data Flow (End-to-End)

```
1. User sends a message from Telegram: "Bu projedeki hatalari bul"
   │
2. TelegramAdapter receives the message and normalizes it:
   │  → InboundMessage(channel="telegram", sender_id="12345678",
   │                    sender_name="Mert", text="Bu projedeki hatalari bul")
   │
3. MessageRouter:
   │  a. Auth: Is sender_id in the allowlist? → YES
   │  b. Session: "telegram:12345678" → session_id
   │  c. Forward to runtime
   │
4. AethonRuntime:
   │  a. Load conversation history from FileSessionManager
   │  b. SystemPromptComposer: SOUL.md + TOOLS.md + CONTEXT.md + SOP list
   │  c. Create/retrieve agent
   │  d. agent("Bu projedeki hatalari bul")
   │
5. Strands Agent Event Loop:
   │  a. Model call → Claude (Opus 4.8 via Meridian)
   │  b. Model decides: call the ask_coder tool
   │  c. BeforeToolCallEvent hook → SecurityHookProvider check
   │  d. Tool runs: Coder Agent takes over
   │  e. Coder Agent runs its own tool loop (shell, editor, etc.)
   │  f. AfterToolCallEvent hook → Result is logged
   │  g. Model is called again → generates final response
   │  h. end_turn
   │
6. AethonRuntime:
   │  a. Save to session
   │  b. Save to long-term memory (if needed)
   │  c. Create OutboundMessage
   │
7. MessageRouter → TelegramAdapter:
   │  → OutboundMessage(channel="telegram", recipient_id="12345678",
   │                     text="3 hata bulundu ve duzeltildi: ...")
   │
8. TelegramAdapter → Telegram message is sent to the user
```

---

## 4. System Prompt Architecture

AETHON's system prompt is composed in layers:

```
┌─────────────────────────────────────┐
│ Layer 1: SOUL.md                    │
│ → Agent personality and behavior    │
│   rules                             │
├─────────────────────────────────────┤
│ Layer 2: TOOLS.md                   │
│ → User preferences,                │
│   conventions                       │
├─────────────────────────────────────┤
│ Layer 3: CONTEXT.md                 │
│ → Current project/work context      │
│   (automatically updated)           │
├─────────────────────────────────────┤
│ Layer 4: SOP List                   │
│ → Available SOP commands            │
│   (name + description only)         │
├─────────────────────────────────────┤
│ Layer 5: Channel Information        │
│ → Active session ID, channel name   │
├─────────────────────────────────────┤
│ Layer 6: Time                       │
│ → datetime.now().isoformat()        │
└─────────────────────────────────────┘
```

**File Locations:**
```
~/.aethon/workspace/
  ├── SOUL.md        → Personality (manually edited)
  ├── TOOLS.md       → Preferences (manually edited)
  ├── CONTEXT.md     → Context (automatic + manual)
  └── sops/          → SOP files
```

---

## 5. Tool Pipeline

### 5.1 Tool Categories

**Strands Built-in Tools (strands-agents-tools):**

| Category | Tools | Import |
|----------|-------|--------|
| File | `file_read`, `file_write`, `editor` | `from strands_tools import file_read` |
| Shell | `shell`, `python_repl` | `from strands_tools import shell` |
| Web | `http_request` | `from strands_tools import http_request` |
| Math | `calculator` | `from strands_tools import calculator` |
| Thinking | `think` | `from strands_tools import think` |
| Time | `current_time` | `from strands_tools import current_time` |
| Memory | `memory`, `mem0_memory` | `from strands_tools import memory` |

**AETHON Custom Tools:**

| Tool | File | Description |
|------|------|-------------|
| `ask_coder` | `aethon/tools/delegate.py` | Delegate a coding task to the coder agent |
| `ask_researcher` | `aethon/tools/delegate.py` | Delegate a research task to the researcher |
| `ask_analyst` | `aethon/tools/delegate.py` | Delegate an analysis task to the analyst |
| `ask_planner` | `aethon/tools/delegate.py` | Delegate a planning task to the planner |
| `manage_memory` | `aethon/tools/memory_tool.py` | Manage long-term memory |
| `update_context` | `aethon/tools/context_tool.py` | Manage CONTEXT.md context |
| `send_message` | `aethon/tools/messaging.py` | Send a message to another channel |
| `schedule_task` | `aethon/tools/scheduler.py` | Schedule a cron-based task |
| `list_scheduled_jobs` | `aethon/tools/scheduler.py` | List scheduled tasks |
| `remove_scheduled_job` | `aethon/tools/scheduler.py` | Remove a scheduled task |

### 5.2 Tool Definition Pattern

```python
from strands import tool

@tool
def ask_coder(task: str) -> str:
    """Delegate a coding task to the coder specialist.

    Args:
        task: Coding task description
    """
    coder = get_specialist("coder")
    result = coder(task)
    return result.message["content"][0]["text"]
```

### 5.3 Hook Pipeline

Every tool call passes through this pipeline:

```
Model produces "tool_use"
        │
        ▼
┌────────────────────┐
│ BeforeToolCallEvent │
│                     │
│ 1. SecurityHook:    │  Dangerous command + workspace check
│    - Blocked cmds   │
│    - Workspace check│
│                     │
│ 2. MemoryGuardHook: │  Sensitive information protection
│    - API key/pass   │  (only for manage_memory store)
│    - Token/SSH/PEM  │
│    - Credit card    │
│                     │
│ 3. TelemetryHook:   │  Start timing
│    - Start timer    │
│                     │
│ 4. ApprovalHook:    │  User approval
│    - Interrupt?     │
└────────┬────────────┘
         │
         ▼
┌───────────────────┐
│   TOOL EXECUTES   │
└────────┬──────────┘
         │
         ▼
┌────────────────────┐
│ AfterToolCallEvent  │
│                     │
│ TelemetryHook:      │
│  - Stop timer       │
│  - Log metric       │
│  - Error tracking   │
└─────────────────────┘
```

**Hook Order:** Security → MemoryGuard → Telemetry → Approval. Security blocks dangerous operations, MemoryGuard protects sensitive data, Telemetry records everything that passes through, Approval requests final user confirmation.

---

## 6. Multi-Agent Architecture

### 6.1 Agent-as-Tool (Default Mode)

```
User message
       │
       ▼
┌──────────────────┐
│  ORCHESTRATOR    │  System Prompt: "You are the main router.
│  (Main Agent)    │  Delegate tasks to specialist agents."
│                  │
│  Tools:          │
│  - ask_coder     │──▶ Coder Agent (independent Strands Agent)
│  - ask_researcher│──▶ Researcher Agent
│  - ask_analyst   │──▶ Analyst Agent
│  - file_read     │
│  - shell         │
│  - think         │
└──────────────────┘
```

The model decides on its own which specialist is needed. The Orchestrator handles simple tasks itself and delegates complex tasks.

### 6.2 Swarm (Collaboration Mode)

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
# result.final_response → Final response
# result.node_history → Which agents ran
```

Agents hand off to each other. The Orchestrator delegates to the planner, the planner to the coder, and so on.

### 6.3 Graph (Pipeline Mode)

```python
from strands.multiagent import GraphBuilder

builder = GraphBuilder()
plan_node = builder.add_node(planner, "planning")
research_node = builder.add_node(researcher, "research")
code_node = builder.add_node(coder, "coding")

builder.add_edge(plan_node, research_node)
builder.add_edge(research_node, code_node)
builder.set_entry_point("planning")

graph = builder.build()
result = graph("Yeni API endpoint implement et")
```

Runs in a deterministic order: Planning → Research → Coding

---

## 7. Memory Architecture

### 7.1 Three-Layer Memory

```
┌─────────────────────────────────────────┐
│           LONG-TERM MEMORY              │
│     (SQLite + Ollama Embeddings)        │
│                                         │
│  User preferences, knowledge,           │
│  learned patterns                       │
│  → Persists for months/years            │
│  → Accessed via semantic search         │
├─────────────────────────────────────────┤
│           SESSION MEMORY                │
│       (FileSessionManager)              │
│                                         │
│  Conversation history, agent state      │
│  → Persists for the session duration    │
│  → Stored as JSON files                 │
│                                         │
│  Directory:                             │
│  sessions/session_{id}/                 │
│    ├── session.json                     │
│    └── agents/agent_{id}/              │
│        ├── agent.json                   │
│        └── messages/message_{n}.json    │
├─────────────────────────────────────────┤
│          WORKING MEMORY                 │
│   (SummarizingConversationManager)      │
│                                         │
│  Last 10 messages + summary of          │
│  previous messages                      │
│  → Refreshed on each model call         │
│  → Fits within the context window       │
└─────────────────────────────────────────┘
```

### 7.2 Vector Memory Detail

```
SQLite Table: memories
┌────────┬─────────┬───────────┬──────────┬───────────┬────────────┐
│ id     │ content │ category  │ embedding│ metadata  │ created_at │
│ INTEGER│ TEXT    │ TEXT      │ TEXT     │ TEXT      │ TEXT       │
│ PK     │         │           │ JSON     │ JSON      │ ISO 8601   │
└────────┴─────────┴───────────┴──────────┴───────────┴────────────┘

Embedding: Ollama /api/embed endpoint
Search: Cosine similarity (computed on the Python side)
```

---

## 8. Configuration Architecture

### 8.1 Config Hierarchy

```
1. Default values (Python code)
   │
2. ~/.aethon/config.yaml (user configuration)
   │
3. Environment variables (${TELEGRAM_BOT_TOKEN})
   │
4. CLI arguments (--port 18790)
```

### 8.2 Config Model (Pydantic)

```python
class ModelConfig(BaseModel):
    provider: str = "ollama"
    host: str = "http://localhost:11434"
    model_id: str = "claude-opus-4-8"
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40

class ChannelConfig(BaseModel):
    enabled: bool = False
    # Channel-specific fields in subclass

class SecurityConfig(BaseModel):
    workspace_only: bool = False  # opt in to confine file tools to the workspace
    require_approval: list[str] = ["shell", "file_write", "send_message"]  # reserved; not wired
    blocked_commands: list[str] = ["rm -rf /", "sudo", "mkfs"]

class AethonConfig(BaseModel):
    model: ModelConfig
    channels: ChannelsConfig
    security: SecurityConfig
    memory: MemoryConfig
    session: SessionConfig
    sops: SOPConfig
    multi_agent: MultiAgentConfig
    telemetry: TelemetryConfig       # Metric collection
    memory_guard: MemoryGuardConfig  # Sensitive information protection
    scheduler: SchedulerConfig       # Cron-based SOP scheduling
    dashboard: DashboardConfig       # Web monitoring panel
    webhook: WebhookConfig           # HTTP webhook support
    mcp: MCPConfig                   # MCP server integration
    performance: PerformanceConfig   # LRU cache + model warm-up
    paths: PathsConfig
```

---

## 9. Directory Structure

```
~/.aethon/                              # User data directory
  ├── config.yaml                       # Main configuration
  ├── workspace/                        # Agent workspace
  │   ├── SOUL.md                       # Personality
  │   ├── TOOLS.md                      # Preferences
  │   ├── CONTEXT.md                    # Context
  │   └── sops/                         # SOP files
  ├── sessions/                         # Session data
  │   └── session_{id}/
  │       ├── session.json
  │       └── agents/
  ├── memory.sqlite                     # Long-term memory
  ├── logs/                             # Log files
  └── credentials/                      # Tokens (0600)

aethon/                                  # Project source code
  ├── pyproject.toml
  ├── aethon/
  │   ├── __init__.py
  │   ├── __main__.py                   # python -m aethon
  │   ├── config.py                     # AethonConfig (17 config models)
  │   ├── gateway/
  │   │   ├── server.py                 # AethonGateway (lifecycle management)
  │   │   ├── router.py                # MessageRouter (session + auth)
  │   │   └── webhooks.py             # Webhook endpoints
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
  │   │   ├── context_updater.py       # CONTEXT.md automatic update
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
  │   │   └── builtin/                 # Built-in SOP files
  │   └── ui/
  │       ├── __init__.py
  │       └── dashboard.py             # Web dashboard + API endpoints
  ├── workspace/                        # Default workspace template
  │   ├── SOUL.md
  │   ├── TOOLS.md
  │   ├── CONTEXT.md
  │   └── sops/
  └── tests/                            # 294 tests
```

---

## 10. Dependency Graph

```
aethon
  ├── strands-agents           # Agent framework (core)
  │   └── strands-agents-tools # 47+ tools
  │   └── strands-agents-sops  # SOP system
  │
  ├── fastapi + uvicorn        # WebChat + Dashboard + Webhook + API
  │   └── websockets           # WS support (chat + telemetry)
  │
  ├── aiogram                  # Telegram
  ├── discord.py               # Discord
  ├── slack-bolt               # Slack
  ├── neonize (optional)       # WhatsApp
  │
  ├── prompt_toolkit + rich    # CLI
  ├── click                    # CLI commands
  │
  ├── pyyaml + pydantic        # Config
  ├── aiosqlite                # Database
  ├── apscheduler              # Scheduler
  └── mcp (optional)           # MCP server integration
```

---

## 11. Port and Endpoint Map

| Service | Port | Endpoint | Protocol |
|---------|------|----------|----------|
| Ollama | 11434 | `/api/chat`, `/api/embed` | HTTP |
| WebChat | 18790 | `/ws/chat` | WebSocket |
| WebChat UI | 18790 | `/ui` | HTTP (static) |
| Dashboard | 18790 | `/dashboard` | HTTP |
| Dashboard API | 18790 | `/api/sessions`, `/api/memory`, `/api/config`, `/api/telemetry`, `/api/scheduler/jobs` | HTTP REST |
| Memory Search | 18790 | `/api/memory/search` | HTTP POST |
| Telemetry Stream | 18790 | `/ws/telemetry` | WebSocket |
| Webhook (Channel) | 18790 | `/webhook/{channel}` | HTTP POST |
| Webhook (Trigger) | 18790 | `/webhook/trigger` | HTTP POST |
| Telegram | - | Bot API polling | HTTPS (outbound) |
| Discord | - | Gateway WebSocket | WSS (outbound) |
| Slack | - | Socket Mode | WSS (outbound) |

**Important:** All locally listening services are bound to `127.0.0.1`. `0.0.0.0` is NOT used.

---

## 12. Performance Optimizations

### 12.1 Session LRU Cache

```
Runtime.agents: OrderedDict (LRU cache)

Access:                          Overflow:
┌───────────┐ move_to_end()     ┌───────────┐ popitem(last=False)
│ session_A │ ──────────────▶   │ oldest    │ ──────────────▶ Save to disk
│ session_B │                   │ session_B │
│ session_C │                   │ session_C │
└───────────┘                   │ session_A │
                                └───────────┘
```

Default size: 10 sessions. Evicted sessions remain on disk (FileSessionManager) and are reloaded when accessed again.

### 12.2 Embedding LRU Cache

Embedding results are cached with `lru_cache` for repeated memory queries. Default size: 100 embeddings.

### 12.3 Model Warm-up

Sends a dummy "Merhaba" request at startup to reduce latency on the first user message.
