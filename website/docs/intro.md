---
id: intro
title: What is AETHON?
sidebar_label: Introduction
slug: /intro
---

# What is AETHON?

> **Bring your own model provider.** AETHON is provider-agnostic: point it at the
> **OpenAI API** (default) or **any OpenAI-compatible endpoint** (vLLM, LM Studio,
> LocalAI, or any service speaking the OpenAI API), the **Anthropic API**, or a
> fully-local **Ollama** model — and it also supports **Bedrock, Gemini, LiteLLM,
> and Mistral**. You run it; you choose the backend.

AETHON is a **personal AI assistant you run yourself**. It is a single Python
package that ships every entry point you need to talk to one persistent,
memory-backed assistant:

- a **terminal CLI** for interactive chat,
- a **Web UI (WebChat)** in your browser,
- **messaging bots** for Telegram, Discord, Slack, and (experimentally) WhatsApp,
- a **live dashboard** to watch sessions, memory, telemetry, agents, and SOPs in real time,
- **webhooks** so other systems can trigger the assistant,
- and a **cron scheduler** so the assistant can run jobs on a timetable.

Under the hood, AETHON is built on the **Strands Agents SDK**. A main orchestrator
agent can delegate to **specialist sub-agents** (Coder, Researcher, Analyst,
Planner), keep **long-term vector memory** of what matters to you, follow **SOPs**
(Standard Operating Procedures — reusable, slash-invoked workflows), and call
**tools** (files, shell, scheduling, messaging, MCP servers).

**You bring the model provider.** AETHON defaults to **OpenAI** (`gpt-4o`): set an
`api_key` for the official OpenAI API, or point `host` at **any OpenAI-compatible
endpoint** — a local server like vLLM, LM Studio, or LocalAI, or any service that
speaks the OpenAI API. Because everything is **local-first** (services bind to
`127.0.0.1` by default and your data lives under `~/.aethon`), you stay in control
of your data and your bill.

:::tip Provider-agnostic by design
Flip one line in your config (`model.provider`) to switch between OpenAI, the
Anthropic API, a fully-local Ollama model, Bedrock, Gemini, LiteLLM, or Mistral.
:::

| | |
|---|---|
| **Author** | Mert Özbaş |
| **Repository** | [github.com/mertozbas/aethon](https://github.com/mertozbas/aethon) |
| **Version** | 0.3.0 |
| **License** | PolyForm Noncommercial 1.0.0 (source-available; free for noncommercial use) |

---

## Feature tour

### Model backends
- **Bring your own provider** — defaults to **OpenAI** (`gpt-4o`) via an API key, **or** any **OpenAI-compatible base URL** (vLLM, LM Studio, LocalAI, …).
- Works with **any Strands provider**: `openai` (default), `anthropic`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral` (plus `fake`/`echo` for testing).
- Run **fully local** with Ollama — no API key, no cloud calls.
- Guided **setup wizard** (`aethon init`) and a **diagnostics** command (`aethon doctor`).

### Channels (all in one package)
- **CLI** — terminal chat with history and Markdown rendering.
- **WebChat** — a browser chat UI served by FastAPI/uvicorn.
- **Telegram, Discord, Slack** — messaging bots (libraries ship with the core install).
- **WhatsApp** — experimental, via the optional `whatsapp` extra.

### Assistant intelligence
- **Long-term vector memory** — SQLite-backed embeddings with cosine-similarity search.
- **Multi-agent specialists** — Coder, Researcher, Analyst, Planner, reachable from the main agent via `ask_*` delegation tools.
- **SOPs** — built-in `/code-assist`, `/pdd`, `/codebase-summary`, plus your own custom `*.sop.md` workflows.
- **Workspace persona files** — `SOUL.md`, `TOOLS.md`, `CONTEXT.md` define identity, preferences, and live state.
- **Core tools** — file read/write/edit, shell, scheduling, context updates, messaging, and MCP tools.
- **Self-improvement** — `record_learning` persists discoveries to `LEARNINGS.md`; the system prompt is **environment-aware** (OS/cwd/shell).

### Capabilities (opt-in tools)
- **Web & APIs** — `scraper` (BeautifulSoup), `use_github` (GitHub GraphQL), `jsonrpc` (HTTP/WebSocket), `notify` (native notifications).
- **macOS native** — `use_mac` (Calendar, Reminders, Mail, Contacts, Safari, Finder, Shortcuts, Messages, Music, Keychain) and `apple_notes`, Darwin-gated with Messages/Keychain off by default.
- **Code intelligence** — `lsp` (diagnostics, go-to-def, references, hover via pyright/gopls/…) + an auto-diagnostics hook.
- **Dynamic tools** — `manage_tools` loads/creates tools at runtime in a subprocess sandbox (gated).
- **Computer control** — `use_computer` (screen/mouse/keyboard, high-risk, off by default, approval-gated).
- **Ambient / autonomous mode** — proactive idle-time work, fully opt-in.
- **Introspection** — `manage_messages` inspects the agent's own conversation, turn-aware.

### Operations & visibility
- **Live dashboard** — overview, Features (capability status), live company (pixel-agents), live monitor, sessions, recordings (session replay), memory, config, logs, agents, SOPs.
- **Session recording & replay** — record the timeline + state snapshots to a ZIP; browse and resume from the dashboard.
- **MCP server** — `aethon mcp` exposes AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over stdio.
- **Scheduler** — cron jobs that run SOPs and deliver results to a channel.
- **Webhooks** — `POST /webhook/trigger` and `POST /webhook/{channel}` with optional HMAC-SHA256 verification.
- **Telemetry** — event history with summaries surfaced in the dashboard.
- **Context safety** — oversized tool output is auto-capped so a single huge command can't overflow the model context.

### Security & privacy
- **Local-first**: services bind to `127.0.0.1` by default; your data lives in `~/.aethon`.
- **Workspace boundary** + **blocked-command** filtering + **approval** hooks.
- **Dashboard auth token**, **secret masking** in API config dumps, and a **memory guard** that keeps secrets out of long-term memory.

:::info New in 0.3.0
The reliability backstop (durable task ledger, verify-before-claim), network
security (deny-by-default exposure, docker shell sandbox, untrusted-content
marking), the token economy (a daily spend ceiling, history compaction, repo
map, scout), and the **[autonomous core loop](./concepts/core-loop.md)**
(intake → plan → bounded executor → proof-of-work receipt). All opt-in. Earlier
0.2.0 additions (capability tools, macOS tools, LSP, dynamic tools, ambient
mode, recording, MCP server) are catalogued under **[Capabilities](./concepts/capabilities.md)**.
:::

---

## Where to next?

- **New here?** Head to **[Installation](./getting-started/installation.md)** for a
  complete first-time walkthrough, then **[Configuration](./getting-started/configuration.md)**.
- **Picking a model?** See **[Model Backends](./getting-started/model-backends.md)**.
- **Want the big picture?** Read **[Architecture](./reference/architecture.md)**.
