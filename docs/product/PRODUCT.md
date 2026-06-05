# AETHON — Product Document

> **AETHON** — Autonomous Execution Through Harmonized Orchestrated Networks
> Version: 1.0.0 | Date: 2026-03-12

---

## 1. Product Summary

AETHON is **a personal AI assistant system that runs on your own machine, is accessible from all messaging channels, and is powered by a multi-agent team.**

- **Single user** — designed as your personal AI assistant
- **Runs locally** — with Ollama on Mac, no cloud dependency
- **Access from anywhere** — WhatsApp, Telegram, Discord, Slack, WebChat, CLI
- **Smart team** — not a single agent, but a specialist agent team
- **Structured workflows** — repeatable tasks with SOPs
- **Security-first** — 7-layer security architecture

---

## 2. Vision

### 2.1 Problem

Current AI assistant systems have the following issues:

1. **Single agent limitation** — Everything is handled by a single agent
2. **Security vulnerabilities** — Externally exposed ports, unvalidated tools
3. **Lack of workflows** — Agent decides on its own, no structured flow
4. **No output validation** — Whatever the agent produces is accepted
5. **No observability** — No awareness of what is happening

### 2.2 Solution

| Problem | AETHON Solution |
|---------|-----------------|
| Single agent | Multi-specialist agent team (Swarm + Graph + Agent-as-Tool) |
| Security vulnerabilities | Loopback-only, no marketplace, hook-based policy |
| Lack of workflows | SOP-driven structured flows |
| Output validation | Mandatory structured output with Pydantic |
| Observability | Telemetry dashboard + live metric stream |

### 2.3 Target User

**Single user: Mert Ozbas**

- Backend developer (Python, asyncio, WebSocket, OOP)
- Works with AI/ML agent systems
- Develops locally on Mac
- Speaks Turkish and English

---

## 3. Core Features

### 3.1 Multi-Channel Access

| Channel | Library | Connection |
|---------|---------|------------|
| CLI | `prompt_toolkit` | Terminal stdin/stdout |
| WebChat | `FastAPI` + `websockets` | HTTP/WS localhost:18790 |
| Telegram | `aiogram` 3.x | Bot Token (BotFather) |
| Discord | `discord.py` 2.x | Bot Token (Developer Portal) |
| Slack | `slack-bolt` | Bot Token + App Token (Socket Mode) |
| WhatsApp | `neonize` / bridge | QR code pairing |

All channels connect to the **same agent runtime**. No matter which channel you write from, the same AETHON responds to you.

### 3.2 Multi-Agent Team

When a task arrives, a specialist team takes over:

| Agent | Expertise | Tools Used |
|-------|-----------|------------|
| **Orchestrator** | Main router, task delegation | All delegate tools |
| **Coder** | Code writing, testing, debugging, refactoring | `editor`, `shell`, `file_write` |
| **Researcher** | Web research, documentation reading | `http_request`, `file_read`, `think` |
| **Analyst** | Data analysis, charting, reporting | `file_write`, `think` |
| **Planner** | Task decomposition, prioritization | `file_read`, `file_write`, `think` |

**3 Operating Modes:**

1. **Agent-as-Tool** — Orchestrator calls specialist agents as tools (`ask_coder(task)`)
2. **Swarm** — Agents hand off tasks to each other (collaboration)
3. **Graph** — Agents run in a specific order (pipeline: Planning → Research → Coding)

### 3.3 SOP Workflows

Standard operating procedures for recurring tasks:

| SOP | Trigger | Description |
|-----|---------|-------------|
| `code-assist` | `/code-assist` | TDD-based code implementation (Explore→Plan→Code→Commit) |
| `pdd` | `/pdd` | Prompt-Driven Development — from idea to design document |
| `codebase-summary` | `/codebase-summary` | Generate comprehensive codebase documentation |
| `morning-brief` | `/morning-brief` | Prepare morning briefing (custom) |
| `weekly-report` | `/weekly-report` | Prepare weekly report (custom) |

**Custom SOP writing support** — You can define your own workflows as markdown.

### 3.4 Scheduler

Cron-based automatic SOP triggering:

```yaml
scheduler:
  enabled: true
  jobs:
    morning-brief:
      cron: "0 9 * * 1-5"     # Weekdays at 9 AM
      sop_name: "morning-brief"
      channel: "telegram"
```

You can also give verbal commands to the agent: "Run morning-brief every day at 9 AM"

### 3.5 Webhook Support

Trigger AETHON from external systems:

```bash
# Channel-based
curl -X POST http://localhost:18790/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello"}'

# SOP trigger
curl -X POST http://localhost:18790/webhook/trigger \
  -d '{"sop_name": "code-assist", "text": "login ekranini yap"}'
```

Secure webhook validation with HMAC-SHA256 secret is supported.

### 3.6 Web Dashboard

Monitor AETHON from the browser: `http://localhost:18790/dashboard`

- **Sessions** — View active sessions
- **Memory** — Search long-term memory contents
- **Telemetry** — Tool/Model call statistics
- **Scheduled Tasks** — View cron jobs
- **Live Metrics** — Real-time stream via WebSocket

### 3.7 MCP Integration

Connect external tools with Model Context Protocol:

```yaml
mcp:
  enabled: true
  servers:
    - command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
```

Tools from MCP servers are automatically added to the agent.

### 3.8 Security-First Design

| Layer | Protection |
|-------|------------|
| Network | Gateway listens only on 127.0.0.1 — external access impossible |
| Identity | Allowlist-based sender verification |
| Tool | Dangerous operations blocked via SecurityHookProvider |
| File | Workspace-only access — access to other directories is blocked |
| Memory | Sensitive information detection via MemoryGuardHook (API key, password, token) |
| Content | Content filtering from external sources |
| Approval | Interrupt-based user approval via ApprovalHookProvider |

### 3.9 Memory System

| Layer | Technology | Lifespan |
|-------|------------|----------|
| Working Memory | SummarizingConversationManager | Each model call |
| Session Memory | FileSessionManager | Duration of session |
| Long-Term Memory | SQLite + Ollama Embeddings | Months/years |

With embedding LRU cache, no repeated API calls for the same text.

### 3.10 Telemetry and Observability

- **TelemetryHookProvider** — Tracks every tool and model call
- **Metrics** — Call count, average duration, error count
- **WebSocket Stream** — Live metric stream at `/ws/telemetry`
- **Dashboard API** — JSON access via `/api/telemetry`

### 3.11 Automatic CONTEXT.md Updates

Automatically updates the current context during agent operation:

```
User: "My current project is HashTrade v2"
AETHON: update_context("project", "HashTrade v2") → CONTEXT.md is updated
```

---

## 4. Technology Stack

### 4.1 Core

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **Agent Framework** | Strands Agents SDK |
| **LLM** | Claude (Opus 4.8) via Meridian — or any Strands provider |
| **Model Provider** | MeridianModel ([strands-meridian](https://github.com/mertozbas/strands-meridian)); OllamaModel / OpenAI / Anthropic also supported |
| **Multi-Agent** | Strands Swarm + GraphBuilder |
| **Tool Ecosystem** | strands-agents-tools (47+ tools) |

### 4.2 Infrastructure

| Component | Technology |
|-----------|------------|
| **Async Runtime** | Python asyncio |
| **Web Framework** | FastAPI + Uvicorn |
| **WebSocket** | websockets / FastAPI WS |
| **CLI** | prompt_toolkit + rich + click |
| **Config** | PyYAML + Pydantic |
| **Database** | SQLite |
| **Scheduler** | APScheduler |
| **Observability** | TelemetryHookProvider + Dashboard |

---

## 5. Model: Claude Opus 4.8 (default)

AETHON defaults to **Claude Opus 4.8** on your Claude Max subscription quota, served through the
local [Meridian](https://github.com/rynfar/meridian) proxy via the
[strands-meridian](https://github.com/mertozbas/strands-meridian) provider. The model is
provider-agnostic — switch to any Strands provider (Ollama, the Anthropic API, OpenAI, …) at any time.

| Property | Value |
|----------|-------|
| Default model | `claude-opus-4-8` (Claude's most capable) |
| Context | 1M tokens (included with Claude Max) |
| Thinking | Adaptive (Opus 4.8 rejects a fixed thinking budget) |
| Tool Calling | Yes |
| Billing | Your Claude subscription quota — no per-token API bills |
| Setup | `npm i -g @rynfar/meridian && claude login` (auto-started by `aethon start`) |

> Sampling parameters (`temperature` / `top_p` / `top_k`) are **not sent** for `claude-opus-4-8`,
> which rejects them; they still apply to the Ollama and OpenAI paths.

**Local alternative — Ollama:** `ollama pull qwen3-coder-next` and set `provider: ollama` in
`config.yaml` (recommended sampling: temperature 1.0, top-p 0.95, top-k 40).

---

## 6. Usage Scenarios

### Scenario 1: Code Development
```
User (Telegram): "implement the login page"
AETHON:
  → Planner: Breaks the task into steps
  → Coder: Implements with TDD (test → code → refactor)
  → Result is reported to the user
```

### Scenario 2: Research
```
User (WhatsApp): "compare FastAPI vs Django"
AETHON:
  → Researcher: Researches on the web, reads documentation
  → Analyst: Analyzes data, creates comparison table
  → Report is sent to the user
```

### Scenario 3: Automatic Morning Briefing
```
Cron (09:00): /morning-brief SOP is triggered
AETHON:
  → SOP steps run sequentially
  → Calendar, tasks, news are checked
  → Briefing is formatted and sent via Telegram
```

### Scenario 4: Integration via Webhook
```
CI/CD Pipeline: POST /webhook/trigger {"sop_name":"codebase-summary"}
AETHON:
  → codebase-summary SOP is triggered
  → Report is generated
  → Result is sent to Slack
```

---

## 7. Project Limitations

### 7.1 Intentional Constraints
- **Single user** — No multi-user support (not needed)
- **Local operation** — No cloud deployment (for security)
- **6 channels** — The most important 6 messaging channels are supported
- **Local-first model** — runs against a local Meridian proxy by default; provider-agnostic

### 7.2 Model Limitations
- Default path needs an active Claude subscription and a running Meridian proxy
- The fully-local Ollama path needs enough RAM for the chosen model
- Tool-calling reliability depends on the selected provider

---

## 8. Success Criteria — COMPLETED

### MVP (Phase 1) ✅
- [x] Ability to chat with AETHON from CLI
- [x] Ability to chat with AETHON from WebChat
- [x] Claude via Meridian (or Ollama) is running
- [x] Basic tools are working (file_read, file_write, shell, editor)
- [x] Session management is working (conversation history is preserved)
- [x] Security hooks are active

### Full Product (Phase 4) ✅
- [x] All 6 channel support (CLI, WebChat, Telegram, Discord, Slack, WhatsApp)
- [x] Multi-agent team is working (Orchestrator, Coder, Researcher, Analyst, Planner)
- [x] SOPs are working (3 built-in + custom SOP support)
- [x] Long-term memory is working (SQLite + Ollama Embeddings)
- [x] Scheduler is working (APScheduler + cron)
- [x] Dashboard is working (7 APIs + WebSocket + UI)
- [x] Webhook support is working (HMAC-SHA256)
- [x] Telemetry is working (TelemetryHookProvider + live stream)
- [x] MemoryGuard is working (sensitive information blocking)
- [x] MCP integration is working (external tool servers)
- [x] Performance optimizations (LRU cache, embedding cache, model warm-up)
- [x] **294 tests passing**

---

## 9. Glossary

| Term | Description |
|------|-------------|
| **Agent** | Combination of LLM + System Prompt + Tools |
| **Swarm** | Agents completing tasks through collaboration |
| **Graph** | Agents running in a specific order |
| **SOP** | Standard Operating Procedure — structured workflow |
| **Hook** | Callback attached to events in the agent lifecycle |
| **Interrupt** | Pausing agent execution to request user approval |
| **Gateway** | Main process coordinating all channel adapters |
| **Adapter** | Module for communicating with a specific messaging platform |
| **Workspace** | Agent's working directory (SOUL.md, TOOLS.md, SOPs) |
| **Orchestrator** | Main agent that routes tasks to appropriate specialist agents |
| **MCP** | Model Context Protocol — standard for connecting external tools to the agent |
| **Webhook** | Trigger point from external systems via HTTP POST |
| **Telemetry** | Mechanism for monitoring and measuring agent performance |
| **MemoryGuard** | Security layer that prevents sensitive information from being written to memory |
