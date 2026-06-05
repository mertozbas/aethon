# AETHON

**Personal AI Assistant** — Local LLM, multi-channel, multi-agent, full control.

> *Autonomous Execution Through Harmonized Orchestrated Networks*

```
Python 3.10+  |  Strands Agents SDK  |  Ollama  |  294 Tests  |  v0.1.0
```

---

## What is AETHON?

AETHON is a locally-running, multi-channel, multi-agent personal AI assistant.

- **Local and private** — All data and model operations stay on your machine. No cloud dependency.
- **6 channels** — Access via CLI, WebChat, Telegram, Discord, Slack, and WhatsApp.
- **Expert team** — Not a single agent; a team of specialists: Coder, Researcher, Analyst, and Planner.
- **SOP system** — Automate repeatable workflows with structured operating procedures.
- **Scheduler** — Run SOPs automatically with cron-based task scheduling.
- **Security-first** — 7-layer security architecture, memory protection, command filtering.

```
┌─────────────────────────────────────────────────────────────┐
│                        CHANNELS                              │
│  CLI  │  WebChat  │  Telegram  │  Discord  │  Slack  │  WA  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  MESSAGE ROUTER │
                   │  + Auth + Queue │
                   └────────┬────────┘
                            │
              ┌─────────────▼─────────────┐
              │      AETHON RUNTIME       │
              │                           │
              │   ┌─────────────────────┐ │
              │   │   ORCHESTRATOR      │ │
              │   │   (Strands Agent)   │ │
              │   └──┬──────┬───────┬───┘ │
              │      │      │       │     │
              │   Coder  Resear  Analyst  │
              │   Agent  cher    Agent    │
              │          Agent            │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │      INFRASTRUCTURE       │
              │  Memory │ Session │ Config │
              │  SQLite │ JSON    │ YAML   │
              └───────────────────────────┘
```

---

## Features

### Multi-Channel Access

| Channel | Technology | Description |
|---------|-----------|-------------|
| CLI | prompt_toolkit + rich | Terminal interface |
| WebChat | FastAPI + WebSocket | Browser-based chat |
| Telegram | aiogram 3.x | Bot API polling |
| Discord | discord.py 2.x | Gateway WebSocket |
| Slack | slack-bolt | Socket Mode |
| WhatsApp | neonize | QR pairing |

### Expert Agent Team

| Agent | Task | Tools |
|-------|------|-------|
| Orchestrator | Routing, simple tasks | All tools + delegation |
| Coder | Coding, debugging, refactoring | shell, editor, file_read/write |
| Researcher | Information gathering, analysis | http_request, file_read |
| Analyst | Data analysis, reporting | python_repl, calculator |
| Planner | Project planning, task distribution | think, file_read |

### SOP Workflows

Built-in SOPs:

| SOP | Command | Description |
|-----|---------|-------------|
| Code Assist | `/code-assist` | Code writing, fixing, refactoring |
| PDD | `/pdd` | Puzzle-Driven Development |
| Morning Brief | `/morning-brief` | Morning briefing report |

Add your custom SOPs to `~/.aethon/workspace/sops/`.

### Memory System

```
Long-Term Memory  ─── SQLite + Ollama Embeddings (semantic search)
Session Memory    ─── FileSessionManager (conversation history)
Working Memory    ─── SummarizingConversationManager (context window)
```

### Dashboard and API

- **Web Dashboard** — Sessions, memory, telemetry, scheduled tasks
- **REST API** — `/api/sessions`, `/api/memory`, `/api/telemetry`, `/api/config`
- **WebSocket** — `/ws/chat` (chat), `/ws/telemetry` (live metrics)
- **Webhook** — `/webhook/{channel}`, `/webhook/trigger` (HMAC-SHA256)

### Scheduler

Cron-based task scheduling with APScheduler:

```yaml
scheduler:
  jobs:
    morning-brief:
      cron: "0 9 * * 1-5"    # Weekdays at 9 AM
      sop_name: morning-brief
      channel: telegram
```

### Security

7-layer security architecture:

1. **Network** — All services bind to `127.0.0.1`, `0.0.0.0` is never used
2. **Identity** — Per-channel user validation (`allowed_senders`)
3. **Tool** — Dangerous command filtering (`blocked_commands`)
4. **File** — Workspace sandboxing
5. **Memory** — MemoryGuard (API key, password, token, SSH, credit card blocking)
6. **Content** — Data limiting via SummarizingConversationManager
7. **Approval** — User confirmation for dangerous tools

---

## Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10+ | 3.12+ |
| RAM | 16 GB | 32 GB+ |
| Disk | 50 GB (for model) | SSD |
| OS | macOS (Apple Silicon) | macOS 14+ |
| Ollama | Latest version | — |

---

## Installation

### Claude via Meridian (default, recommended)

AETHON ships configured for **Claude on your Claude Max subscription quota** via the local
[Meridian](https://github.com/rynfar/meridian) proxy and the
[strands-meridian](https://github.com/mertozbas/strands-meridian) provider — no per-token API bills:

```bash
npm install -g @rynfar/meridian
claude login          # one-time
meridian              # proxy on http://127.0.0.1:3456
```

Then install AETHON (step 3) and run — `provider: meridian` is the default, on `claude-opus-4-8`
(Claude's most capable model; 1M context included with Claude Max). Switch models any time with
`model_id` (`claude-opus-4-8`, `claude-sonnet-4-6`, `opus[1m]`, …). The Ollama steps below are
only needed for fully-local inference.

---

### 1. Install Ollama (local alternative)

```bash
brew install ollama
ollama serve
```

### 2. Download Models

```bash
ollama pull qwen3-coder-next      # a local LLM (only for the Ollama path; Claude via Meridian is the default)
ollama pull nomic-embed-text       # embedding model
```

### 3. Install AETHON

```bash
git clone <repo-url> aethon
cd aethon
pip install -e ".[all]"
```

For specific features only:

```bash
pip install -e "."                  # Core only (CLI + WebChat)
pip install -e ".[channels]"        # + Telegram, Discord, Slack
pip install -e ".[memory]"          # + Vector memory
pip install -e ".[scheduler]"       # + Scheduler
pip install -e ".[mcp]"             # + MCP server integration
```

### 4. Configuration (Optional)

On first run, `~/.aethon/` is created automatically. To customize:

```bash
mkdir -p ~/.aethon
cat > ~/.aethon/config.yaml << 'EOF'
model:
  provider: meridian                 # Claude on your Claude Max quota (default)
  model_id: claude-opus-4-8          # most capable; 1M context included with Claude Max
  # provider: ollama                 # local alternative:
  # model_id: qwen3-coder-next
  # host: http://localhost:11434

memory:
  enabled: true
  embedding_model: nomic-embed-text

channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 18790
EOF
```

To use the OpenAI API instead:

```yaml
model:
  provider: openai
  model_id: gpt-5-mini-2025-08-07
  api_key: ${OPENAI_API_KEY}

memory:
  embedding_provider: openai        # or "ollama"
  embedding_model: text-embedding-3-small
  embedding_api_key: ${OPENAI_API_KEY}
```

---

## Getting Started

### Launch

```bash
python -m aethon start
```

or:

```bash
aethon start
```

Output:

```
Starting AETHON...

  Provider: meridian
  Model: claude-opus-4-8
  WebChat: http://127.0.0.1:18790
  Memory: nomic-embed-text (active)
  Multi-Agent: active
  SOPs: 5 loaded
  Scheduler: active
  Telemetry: active
  Dashboard: http://127.0.0.1:18790/dashboard
  Channels: CLI, WebChat

AETHON>
```

### CLI Usage

```
AETHON> Hello, what shall we work on today?
AETHON> Find and fix the bugs in this Python file
AETHON> /code-assist Write a new REST API endpoint
AETHON> Schedule a briefing at 9 AM
```

### WebChat

Open `http://127.0.0.1:18790/ui` in your browser.

### Dashboard

`http://127.0.0.1:18790/dashboard` — Sessions, memory, telemetry, scheduled tasks.

### Webhook

```bash
# Trigger SOP
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"sop_name": "morning-brief", "channel": "telegram"}'

# Plain message
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the project status?"}'
```

---

## Workspace Files

Control AETHON's behavior with 3 files:

| File | Location | Description |
|------|----------|-------------|
| `SOUL.md` | `~/.aethon/workspace/SOUL.md` | Agent personality and behavioral rules |
| `TOOLS.md` | `~/.aethon/workspace/TOOLS.md` | User preferences and conventions |
| `CONTEXT.md` | `~/.aethon/workspace/CONTEXT.md` | Current context (auto-updated) |

**SOUL.md Example:**
```markdown
# AETHON — Personality

You are AETHON, Mert's personal AI assistant.
You run on Mac via Ollama.

## Behavior
- You can communicate in Turkish and English.
- Keep responses concise and to the point.
- Acknowledge mistakes and correct them.
```

---

## Channel Configuration

### Telegram

```yaml
channels:
  telegram:
    enabled: true
    token: "${TELEGRAM_BOT_TOKEN}"

security:
  allowed_senders:
    telegram: ["12345678"]
```

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
```

### Discord

```yaml
channels:
  discord:
    enabled: true
    token: "${DISCORD_BOT_TOKEN}"
```

### Slack

```yaml
channels:
  slack:
    enabled: true
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
```

---

## Directory Structure

```
~/.aethon/                       # User data directory
  ├── config.yaml                # Configuration
  ├── workspace/                 # Agent workspace
  │   ├── SOUL.md                # Personality
  │   ├── TOOLS.md               # Preferences
  │   ├── CONTEXT.md             # Context
  │   └── sops/                  # Custom SOP files
  ├── sessions/                  # Conversation histories
  ├── memory.sqlite              # Long-term memory
  ├── logs/                      # Log files
  └── credentials/               # Tokens

aethon/                          # Project source code
  ├── pyproject.toml
  ├── aethon/
  │   ├── config.py              # AethonConfig (17 Pydantic models)
  │   ├── gateway/               # Gateway + Router + Webhooks
  │   ├── channels/              # 6 channel adapters
  │   ├── agent/                 # Runtime + Hooks + Specialists
  │   ├── tools/                 # Tools (delegate, memory, context, scheduler, MCP)
  │   ├── memory/                # VectorMemory (SQLite + Ollama embeddings)
  │   ├── sops/                  # SOPRunner + built-in SOPs
  │   └── ui/                    # Web dashboard
  └── tests/                     # 294 tests
```

---

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/test_config.py -v

# Integration tests (requires Ollama)
pytest tests/test_integration.py -v
```

### Test Status

| Phase | Test Count | Status |
|-------|------------|--------|
| Phase 1 — Core | 64 | Passing |
| Phase 2 — Channels + Memory | 120 | Passing |
| Phase 3 — Multi-Agent + SOP | 178 | Passing |
| Phase 4 — Polish | 294 | Passing |

### Dependencies

```
strands-agents         — Agent framework (core)
strands-agents-tools   — 47+ tools
fastapi + uvicorn      — WebChat + Dashboard + Webhook + API
aiogram                — Telegram
discord.py             — Discord
slack-bolt             — Slack
apscheduler            — Scheduler
pyyaml + pydantic      — Config
mcp (optional)         — MCP server integration
```

---

## Documentation

Detailed documentation is in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [Product Overview](docs/product/PRODUCT.md) | Features, architecture overview |
| [Getting Started](docs/product/GETTING-STARTED.md) | Installation and quick start |
| [Configuration Reference](docs/product/CONFIGURATION.md) | All settings |
| [API Reference](docs/product/API-REFERENCE.md) | HTTP, WebSocket, webhook, tools |
| [Architecture](docs/product/ARCHITECTURE.md) | Technical architecture and data flows |
| [Security](docs/development/SECURITY.md) | Security model and threat analysis |
| [Roadmap](docs/development/ROADMAP.md) | Project development phases |

---

## Technology

| Layer | Technology |
|-------|-----------|
| Agent Framework | [Strands Agents SDK](https://github.com/strands-agents/sdk-python) |
| LLM | Claude (Opus 4.8) via [Meridian](https://github.com/mertozbas/strands-meridian) on your Claude Max quota — or any [Strands provider](https://github.com/strands-agents/sdk-python) (Ollama, Anthropic API, OpenAI, …) |
| Embedding | nomic-embed-text via Ollama |
| Gateway | FastAPI + Uvicorn |
| CLI | prompt_toolkit + rich + click |
| Database | SQLite (memory), JSON (session) |
| Scheduler | APScheduler |
| Config | PyYAML + Pydantic v2 |

---

## License

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for any noncommercial use
(personal, research, education, hobby). Commercial use is not permitted. This is a
source-available license, not an OSI-approved open-source license.
