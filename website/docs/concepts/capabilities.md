---
id: capabilities
title: Capabilities
sidebar_label: Capabilities
---

# Capabilities

A reference for AETHON's optional capabilities. Everything here is **config-gated**;
powerful/host-affecting features default **off** and route through the security &
approval hooks. Browse live status in the dashboard's **Features** panel.

:::info Design principle
Capabilities plug into the existing runtime via the standard tool/hook extension
points; nothing bypasses the security or approval gates, and heavy/optional
dependencies are isolated as `pip` extras.
:::

## Capability tools (`capabilities` block)

| Tool | What it does | Enable | Notes |
|---|---|---|---|
| `scraper` | BeautifulSoup HTML/XML scraping & parsing | `capabilities.scraper.enabled` (on) | extra: `scraper` (beautifulsoup4) |
| `use_github` | GitHub GraphQL queries + mutations | `capabilities.github.enabled` (on) | reads `$GITHUB_TOKEN`; mutations are approval-aware |
| `jsonrpc` | JSON-RPC over HTTP/WebSocket | `capabilities.jsonrpc.enabled` (on) | auth redacted in logs |
| `notify` | Native macOS notification / bell / speech | `capabilities.notify.enabled` (on) | `method: auto` by default |
| `use_computer` | Screen / mouse / keyboard automation | `capabilities.computer.enabled` (**off**) | ⚠ high-risk; extra `computer` (pyautogui); macOS Accessibility permission; approval-gated |
| `manage_messages` | Turn-aware introspection of the agent's own conversation | always on | read-only |

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
symbols via language servers (pyright/typescript-language-server/gopls/rust-analyzer/
clangd, spawned on demand). Off by default to avoid starting servers on boot.

- `lsp.enabled` registers the tool; `lsp.auto_diagnostics` appends diagnostics after file-modifying tools (home-scoped, capped).
- Extra `lsp` installs pyright; install other language servers on PATH yourself.

## Dynamic tool loading — `manage_tools` (`runtime_tools` block)

Create/fetch/add/reload/remove tools at runtime, validated in a **subprocess sandbox**
before loading. Off by default. Three gating layers:

1. `runtime_tools.enabled` gates registration entirely.
2. The security hook blocks `create`/`fetch` unless `allow_create`, and `add`/`reload` unless `allow_install`.
3. An in-tool check (reading the injected config) refuses dangerous actions when disabled. Read-only actions (`list`/`discover`/`sandbox`) are always allowed; the approval hook prompts only for the code-loading actions.

When need-driven tooling is active (`runtime_tools.enabled`), an Operating Rule in the
system prompt tells the agent that if a task needs a capability no current tool
provides, it should load an existing runtime tool — or, when permitted, create a new
one — via `manage_tools` and continue, instead of giving up or faking the result.
New-tool creation stays approval-gated.

## Ambient / autonomous mode (`ambient` block)

A background loop that does proactive (idle-triggered) or autonomous (continuous) work.
**Dormant by default** — with `ambient.enabled=false` no tools register and no task
runs. `start_ambient_mode` / `stop_ambient_mode` / `get_ambient_status` are the runtime
switch. Iterations run on a dedicated session (no collision with live chats), offloaded
to a thread executor (no message starvation), and a server-side completion signal stops
autonomous runs. `auto_start` is off by default.

When `core_loop.executor_enabled` is on and a project is active in the task ledger, an
ambient tick drives the autonomous core loop: it works the planned project toward
completion via the bounded `ProjectExecutor` (iteration / budget / attempt caps), then
delivers a proof-of-work receipt. Off by default — see
**[The autonomous core loop](./core-loop.md)**.

## Session recording & replay (`session_recorder` block)

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
- `include_recent_logs` (on) — tail of `<paths.logs>/aethon.log` (a rotating file handler feeds it).
- `include_shell_history` (**off**, privacy) — recent bash/zsh history.
- `include_self_awareness` (**off**) — embeds key source files (heavy; slows turns).

## Context-overflow protection (`performance.max_tool_output_chars`)

A tool that dumps thousands of lines (ruff, mypy, big greps) would otherwise overflow
the model's context. Oversized tool output is capped (default ~12000 chars, head + tail
+ a truncation marker) before it reaches the model. Set to `0` to disable.

## Capability diet (`core_loop.capability_diet`)

Every turn carries the full schema of every loaded tool, and a few tools have large
schemas. With `core_loop.capability_diet` on (default **off**), an always-on core
toolset is kept and the heavy, domain-specific tools (`use_mac`, `use_computer`,
`use_github`, `apple_notes`, `scraper`, `jsonrpc`) are pulled into a session only when
its building message matches their keywords. The decision is made once per session (not
per turn) so the prompt/tool cache stays warm. See
**[Token economy](./token-economy.md)** for the rest of the token-economy subsystem.

## macOS menu-bar launcher (`launcher-macos` extra)

`aethon-menubar` is an optional `rumps` menu-bar app (Start/Stop server, open WebChat,
settings) installed with the `launcher-macos` extra.
