---
id: tools
title: Agent tools & telemetry
sidebar_label: Agent tools
---

# Agent tools

The main agent always has: `file_read, file_write, editor, shell, think,
current_time`, plus `update_context` (maintains `CONTEXT.md`), `send_message` (pushes
to any enabled channel), and `manage_messages` (turn-aware introspection of its own
conversation). When the task ledger is active (the default), it also has
`manage_tasks` — the durable task ledger (`workspace/TASKS.json`): `create / update /
complete / list` tasks with `acceptance_criteria`, `evidence`, `parent_id`,
`depends_on`, `priority`, and `due`. The ledger is the durable working state that
survives session resets and restarts, and the core-loop planner/executor read and
write it.

Conditionally added:

- **memory** — `manage_memory(action, content, query, category, memory_id)` when vector memory is active.
- **delegate** — `ask_coder / ask_researcher / ask_analyst / ask_planner / ask_scout / ask_specialist` when the multi-agent system is on; plus `manage_specialists` when `core_loop.dynamic_specialists` is enabled.
- **scheduler** — `schedule_task`, `list_scheduled_jobs`, `remove_scheduled_job` when the scheduler is running.
- **capabilities** — `scraper`, `use_github`, `jsonrpc`, `notify` (config-gated under `capabilities`, default on).
- **learning** — `record_learning(category, content)` when `prompt.include_learnings` (persists to `LEARNINGS.md`).
- **macOS** (Darwin) — `use_mac`, `apple_notes` when `macos.enabled`.
- **code intelligence** — `lsp` when `lsp.enabled`.
- **dynamic tools** — `manage_tools` when `runtime_tools.enabled` (sandboxed; gated by approval/security).
- **computer control** — `use_computer` when `capabilities.computer.enabled` (needs the `computer` extra).
- **ambient** — `start_ambient_mode / stop_ambient_mode / get_ambient_status` when `ambient.enabled`.
- **MCP tools** — appended when MCP is enabled.

See **[Capabilities](./capabilities.md)** for the opt-in tools and their gates.

## Telemetry

The telemetry hook records events (up to `telemetry.max_history`, default 10000) and
surfaces summaries and recent metrics in the dashboard (`/api/telemetry`, the Live
Monitor, and Agents/history views).

```yaml
telemetry:
  enabled: true
  max_history: 10000
```
