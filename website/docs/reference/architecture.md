---
id: architecture
title: Architecture
sidebar_label: Architecture
---

# Architecture

AETHON is a Strands-Agents application with a single FastAPI/uvicorn server (owned by
the WebChat adapter) that also hosts the dashboard and webhook routers, so everything
shares one host/port. A **gateway** instantiates the enabled **channel adapters** and
routes inbound messages to the **agent runtime**, which composes a system prompt from
the workspace files, holds the **vector memory**, wires up the **specialist factory**
and **SOP runner**, and exposes the **tools**. Cross-cutting **hooks** provide
telemetry, approval, and the memory guard. Optional **MCP** servers extend the toolset.

```
            ┌──────────────────────────────────────────────┐
            │                  Gateway                      │
            │  (starts only the enabled channel adapters)   │
            └──────────────────────────────────────────────┘
              │        │        │        │         │
            CLI     WebChat   Telegram  Discord   Slack ...
              │        │ (FastAPI/uvicorn: WebChat + dashboard + webhooks)
              ▼        ▼
            ┌──────────────────────────────────────────────┐
            │               Agent Runtime                   │
            │  system prompt ← SOUL/TOOLS/CONTEXT + layers  │
            │  ┌────────────┐  ┌──────────┐  ┌───────────┐  │
            │  │ Specialist │  │  Vector  │  │   SOP     │  │
            │  │  factory   │  │  memory  │  │  runner   │  │
            │  └────────────┘  └──────────┘  └───────────┘  │
            │         tools  ·  hooks (telemetry/approval/   │
            │                    memory guard)  ·  MCP       │
            └──────────────────────────────────────────────┘
```

## Layers

- **Channels** — adapters for each entry point (CLI, WebChat, Telegram, Discord, Slack, WhatsApp). The gateway starts only the enabled ones and keeps running if one fails to start.
- **Runtime** — composes the system prompt from the workspace persona files (plus optional environment/learnings/logs layers), owns the orchestrator agent, and exposes the tool set.
- **Specialists** — Coder / Researcher / Analyst / Planner sub-agents reached via `ask_*` delegation tools.
- **Memory** — a SQLite vector store with provider embeddings and cosine-similarity search.
- **SOPs** — built-in and custom slash-invoked workflows.
- **Hooks** — telemetry, approval gating, and the memory guard wrap tool calls.
- **MCP** — optional external MCP servers extend the toolset; `aethon mcp` exposes AETHON's own tools to MCP clients.

## Deeper reference

The repository carries full design documents under
[`docs/`](https://github.com/mertozbas/aethon/tree/main/docs):

- [`docs/product/ARCHITECTURE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/ARCHITECTURE.md) — system architecture, data flows, component relationships.
- [`docs/product/PRODUCT.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/PRODUCT.md) — product overview.
- [`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md) — HTTP/WebSocket API reference.
- [`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md) — security model & threat analysis.
- [`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md) — roadmap.
