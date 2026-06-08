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

## 0.2.0 — capability expansion (current release)

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
- Real-time **voice** (STT/TTS).

See [`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md)
for details.
