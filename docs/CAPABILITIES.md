# AETHON Capabilities

A reference for AETHON's optional capabilities. Everything here is **config-gated**;
powerful/host-affecting features default **off** and route through the security &
approval hooks. Browse live status in the dashboard's **Features** panel, or see the
[README configuration reference](../README.md#capabilities--runtime-features-opt-in)
for the exact YAML.

> Design principle: capabilities plug into the existing runtime via the standard
> tool/hook extension points; nothing bypasses the security or approval gates, and
> heavy/optional dependencies are isolated as `pip` extras.

## Capability tools (`capabilities` block)

| Tool | What it does | Enable | Notes |
|---|---|---|---|
| `scraper` | BeautifulSoup HTML/XML scraping & parsing | `capabilities.scraper.enabled` (on) | extra: `scraper` (beautifulsoup4) |
| `use_github` | GitHub GraphQL queries + mutations | `capabilities.github.enabled` (on) | reads `$GITHUB_TOKEN`; mutations are approval-aware |
| `jsonrpc` | JSON-RPC over HTTP/WebSocket | `capabilities.jsonrpc.enabled` (on) | auth redacted in logs |
| `notify` | Native macOS notification / bell / speech | `capabilities.notify.enabled` (on) | `method: auto` by default |
| `use_computer` | Screen / mouse / keyboard automation | `capabilities.computer.enabled` (**off**) | ⚠ high-risk; extra `computer` (pyautogui); macOS Accessibility permission; approval-gated |
| `manage_messages` | Turn-aware introspection of the agent's own conversation | always on | read-only |
| `record_learning` | Persist a durable learning to `LEARNINGS.md` | `prompt.include_learnings` (on) | read back into the system prompt |

The security hook logs scraper URLs and redacts the GitHub token / JSON-RPC auth.

## macOS native (`macos` block, Darwin only)

`use_mac` (Calendar, Reminders, Mail, Contacts, Safari, Finder, System Events,
Shortcuts, Messages, Music, Keychain, raw AppleScript/JXA) and `apple_notes`
(list/view/search/export + create/edit/append/delete/move).

- Registered only on macOS **and** when `macos.enabled`.
- **Messages and Keychain are off by default** (`enable_messages`, `enable_keychain`); the security hook hard-blocks those action groups while disabled.
- The approval hook gates `macos.actions_requiring_approval` (default `mail.send`, `messages.send`, `keychain.set`); keychain passwords are redacted from logs.
- Extra `macos` adds richer Markdown for `apple_notes` (it degrades gracefully without it).

## Code intelligence — LSP (`lsp` block)

`lsp` provides diagnostics, go-to-definition, find-references, hover, and document
symbols via language servers (pyright/typescript-language-server/gopls/rust-analyzer/clangd,
spawned on demand). Off by default to avoid starting servers on boot.

- `lsp.enabled` registers the tool; `lsp.auto_diagnostics` appends diagnostics after
  file-modifying tools (home-scoped, capped).
- Extra `lsp` installs pyright; install other language servers on PATH yourself.

## Autonomous core loop (`core_loop` block)

The core loop turns a clear unit of work into intake → plan → execute → deliver-with-proof.
Every stage is **opt-in and off by default**; with the flags unset AETHON behaves as a
plain conversational agent.

- **Intake** (`core_loop.intake_enabled`, off) — classifies an incoming message as chat vs.
  a unit of work and opens a tracked task for the latter.
- **Plan → ledger** — a plan is recorded and surfaced; `core_loop.plan_approval` (off) gates
  whether the plan needs a go-ahead before execution.
- **Executor** (`core_loop.executor_enabled`, off) — a bounded run that works the task
  ledger to done. Hard caps: `executor_max_iterations` (20 turns per run) and
  `executor_max_task_attempts` (3 no-progress turns before a task is abandoned).
- **Pulse & receipt** — `pulse_enabled` (on) emits progress pulses while executing
  (silenceable); `receipt_enabled` (on) delivers a proof-of-work receipt when a run ends.

State lives in the durable task ledger (`workspace/TASKS.json`), managed by the
`manage_tasks` tool — tasks carry acceptance criteria and are completed *with* verification
evidence, surviving session resets and restarts.

## Specialist delegation & dynamic specialists (`core_loop` block)

The main agent can delegate to built-in specialists — `ask_coder`, `ask_researcher`,
`ask_analyst`, `ask_planner`, and `ask_scout` — each running with its own tools and
returning only its result. `ask_scout` is a "read many, return little" investigator: it
reads the sources you point it at and returns a concise conclusion, keeping bulk output out
of the main context.

`manage_specialists` (opt-in via `core_loop.dynamic_specialists`, off) lets the agent create
custom specialists at runtime, persisted to `workspace/specialists/*.json` and reachable via
`ask_specialist(name, task)`. A custom specialist may only hold powerful/host-affecting
tools when `core_loop.allow_powerful_specialists` is also set; the tool allowlist is gated
at resolution time. `manage_specialists` is on the default approval list.

## Capability diet & need-driven tools (`core_loop.capability_diet`)

`core_loop.capability_diet` (off) trims the tool surface the model sees to what the current
work needs, reducing prompt weight; tools are surfaced on demand rather than all at once.

## Token economy (history compaction, repo map, recall)

A set of measures keep token spend honest; all are opt-in or cache-safe:

- **History compaction** (`session.compact_enabled`, off) — older tool outputs are batched
  and compacted (cache-aware), keeping the most recent turns intact
  (`compact_keep_last_n_turns`, default 4). See also `performance.max_tool_output_chars`
  below.
- **Repo map** (`repo_map.enabled`, off) — files the agent reads are summarised
  (path → purpose/symbols/hash) in `workspace/REPO_MAP.json` and a compact map is injected
  into the prompt, so the next session is oriented without re-reading. Cache-safe and capped
  (`max_files` 100, `max_snapshot_chars` 2000).
- **Token budget** (`budget` block) — every turn's usage is measured; with
  `budget.daily_usd` set (`0` = measure only) turns are warned near the ceiling
  (`warn_ratio`, default 0.8). `budget.pricing` overrides the built-in USD/1M-token table.
- **Memory recall** (`memory.auto_recall`, off) — relevant long-term memories are recalled
  and injected into context (`recall_top_k` 3, `recall_min_score`, `recall_max_chars` 1500).
  Embeddings come from `memory.embedding_provider` (`ollama` or `openai`).

## Reliability backstop (`reliability` block, Phase 8)

Verification hooks that catch regressions without adding friction. **All gates are advisory
by default** (they append feedback, mirroring the LSP diagnostics pattern); `reliability.strict`
(off) flips them to hard gates.

- `post_edit_verify` (on) — runs a verify command on edited files (`verify_cmd`,
  auto-detects `ruff check` on Python files when unset) and appends a `[Verify]` PASS/FAIL block.
- `completion_gate` (on) — when a reply claims success without verification evidence,
  appends a Definition-of-Done reminder instead of returning the claim clean.
- `anglicization_guard` (on) — advisory pause when an edit replaces existing Turkish text
  with English-only text.
- `input_validator` (on) — cancels malformed tool calls (empty shell command, missing path)
  with a self-describing reason.

## Dynamic tool loading — `manage_tools` (`runtime_tools` block)

Create/fetch/add/reload/remove tools at runtime, validated in a **subprocess
sandbox** before loading. Off by default. Three gating layers:

1. `runtime_tools.enabled` gates registration entirely.
2. The security hook blocks `create`/`fetch` unless `allow_create`, and `add`/`reload`
   unless `allow_install`.
3. An in-tool check (reading the injected config) refuses dangerous actions when
   disabled. Read-only actions (`list`/`discover`/`sandbox`) are always allowed; the
   approval hook prompts only for the code-loading actions.

## Ambient / autonomous mode (`ambient` block)

A background loop that does proactive (idle-triggered) or autonomous (continuous)
work. **Dormant by default** — with `ambient.enabled=false` no tools register and no
task runs. `start_ambient_mode` / `stop_ambient_mode` / `get_ambient_status` are the
runtime switch. Iterations run on a dedicated session (no collision with live chats),
offloaded to a thread executor (no message starvation), and a server-side completion
signal stops autonomous runs. `auto_start` is off by default.

## Session recording & replay (`session_recorder` block, `paths.recordings`)

Records the session timeline (tool calls/results, model calls) plus state snapshots
after each turn, exported to a ZIP on shutdown. Off by default. Browse and resume from
the dashboard's **Recordings** tab (list / events / snapshots / replay preview). The
replay preview never mutates the live agent or the server's working directory.

## MCP server — `aethon mcp`

`aethon mcp` serves AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over
stdio. Tools are invoked through the hook chain (security applies); approval-required
tools are denied (no interactive channel over stdio); tool stdout is diverted so it
can't corrupt the JSON-RPC stream. `runtime.get_tools_schemas()` advertises the schemas.

## System-prompt awareness (`prompt` block)

Optional, individually-gated layers folded into the system prompt:

- `include_environment` (on) — OS/arch/Python/cwd/home/shell/host.
- `include_learnings` (on) — `LEARNINGS.md`, written by the `record_learning` tool.
- `include_recent_logs` (**off**, opt-in) — tail of `<paths.logs>/aethon.log` (a rotating file handler feeds it). Off by default: the log tail changes every turn, so injecting it would defeat provider prompt caching for little orientation value (E1).
- `include_shell_history` (**off**, privacy) — recent bash/zsh history.
- `include_self_awareness` (**off**) — embeds key source files (heavy; slows turns).

## Context-overflow protection (`performance.max_tool_output_chars`)

A tool that dumps thousands of lines (ruff, mypy, big greps) would otherwise overflow
the model's context. Oversized tool output is capped (default ~12000 chars, head + tail
+ a truncation marker) before it reaches the model. Set to `0` to disable.

## macOS menu-bar launcher (`launcher-macos` extra)

`aethon-menubar` is an optional `rumps` menu-bar app (Start/Stop server, open WebChat,
settings) installed with the `launcher-macos` extra.
