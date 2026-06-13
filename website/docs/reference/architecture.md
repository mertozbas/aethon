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
the command/security guard, approval gating, the memory guard, telemetry, and the
opt-in reliability and token-economy hooks. Optional **MCP** servers extend the toolset.

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
            │   tools · hooks (security/approval/memory/     │
            │   telemetry + reliability + token economy)·MCP │
            └──────────────────────────────────────────────┘
```

## Layers

- **Channels** — adapters for each entry point (CLI, WebChat, Telegram, Discord, Slack, WhatsApp). The gateway starts only the enabled ones and keeps running if one fails to start.
- **Runtime** — composes the system prompt from the workspace persona files (plus optional environment/learnings/logs layers), owns the orchestrator agent, and exposes the tool set.
- **Specialists** — Coder / Researcher / Analyst / Planner / Scout sub-agents reached via `ask_*` delegation tools, plus user-defined specialists created at runtime (`manage_specialists`, reached via `ask_specialist`). Both Scout (read-many/return-little) and dynamic specialists are opt-in (`core_loop.dynamic_specialists`).
- **Memory** — a SQLite vector store with provider embeddings and cosine-similarity search.
- **SOPs** — built-in and custom slash-invoked workflows.
- **Hooks** — the command/security guard, approval gating, the memory guard, and telemetry wrap tool calls, alongside the Phase 8 reliability hooks (verify-on-edit, completion gate, input validation, anglicization guard) and the untrusted-content marker. All reliability gates are advisory-by-default unless `reliability.strict` is set.
- **MCP** — optional external MCP servers extend the toolset; `aethon mcp` exposes AETHON's own tools to MCP clients.

## Deeper reference

The repository carries full design documents under
[`docs/`](https://github.com/mertozbas/aethon/tree/main/docs):

- [`docs/product/ARCHITECTURE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/ARCHITECTURE.md) — system architecture, data flows, component relationships.
- [`docs/product/PRODUCT.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/PRODUCT.md) — product overview.
- [`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md) — HTTP/WebSocket API reference.
- [`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) — security model & threat analysis.
- [Roadmap](../project/roadmap.md) — shipped phases and what's still deferred.
