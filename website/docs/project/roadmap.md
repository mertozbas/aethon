---
id: roadmap
title: Roadmap
sidebar_label: Roadmap
---

# Roadmap

**v1 (0.1.0) shipped:** the full provider-agnostic assistant — CLI + WebChat +
dashboard, Telegram/Discord/Slack channels, SQLite vector memory, multi-agent
specialists with `ask_*` delegation, built-in and custom SOPs, scheduler, webhooks,
telemetry, bring-your-own model provider (OpenAI default, plus Anthropic / Ollama /
Bedrock / Gemini / LiteLLM / Mistral), and Docker + CI infrastructure.

## 0.3.0 — reliability, security & the core loop (current release)

- **Reliability backstop (Phase 8)** — a verification layer wired into tool calls: verify-on-edit, a completion gate, input validation, and an anglicization guard, plus a durable task ledger. All gates are advisory-by-default; `reliability.strict` flips them to hard gates.
- **Network security (Phase 9A)** — deny-by-default auth on the shared app, Origin validation on WebSocket upgrades, a non-loopback bind that **fails closed** without `dashboard.auth_token`, default-deny sender allowlists on the messaging bots, fail-closed webhook verification, an opt-in docker execution sandbox (`security.sandbox: docker`), and untrusted-content marking for external tool/webhook output.
- **Robustness & token economy (Phase 9B)** — single-instance locking, per-session turn serialization, adapter supervision with backoff, persisted schedules (and one-shot reminders), disk-retention pruning, user-facing error replies, a token meter with a daily spend ceiling (`budget.daily_usd`), and prompt-cache layer ordering.
- **Autonomous core loop (Phase 10)** — opt-in work intake → plan → bounded executor → proof-of-work receipt, with hard runaway guards (iteration cap, durable per-task attempt limit, budget ceiling). Plus a capability diet, runtime-defined dynamic specialists, a read-heavy Scout specialist, history compaction, a repo map, and embedding-robustness with opt-in memory auto-recall.

Everything above is **opt-in / off by default** unless noted; the network-security defaults are the exception (they harden by default).

## 0.2.0 — capability expansion

- **Capability tools** — `scraper`, `use_github`, `jsonrpc`, `notify`, `manage_messages`.
- **macOS native** — `use_mac` + `apple_notes` (Darwin-gated; Messages/Keychain off by default).
- **Code intelligence** — `lsp` tool + auto-diagnostics hook.
- **Dynamic tool loading** — `manage_tools` with a subprocess sandbox + 3-layer gating.
- **Computer control** — `use_computer` (opt-in, approval-gated).
- **Ambient / autonomous mode** — proactive idle-time work (opt-in).
- **Session recording & replay** — recorder hook + replay API + dashboard tab.
- **MCP server** — `aethon mcp` exposes the toolset to MCP clients.
- **System-prompt awareness** — environment / learnings / recent-logs / shell-history layers + `record_learning`.
- **Dashboard** — Features panel + identity-correct Live Company + context-overflow protection.

## Still deferred

- Response **streaming**.
- **Team / pipeline orchestration** (Swarm/Graph) wired into the runtime and exposed as a command/tool.
- **Per-specialist multi-model** configuration.
- **Retrieval-augmented generation** (RAG) over indexed documents.
- Real-time **voice** (STT/TTS) and **vision** — deferred to a future capability phase.

For the detailed per-release record, see the
[`CHANGELOG`](https://github.com/mertozbas/aethon/blob/main/CHANGELOG.md).
