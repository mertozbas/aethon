---
id: configuration
title: Configuration Reference
sidebar_label: Configuration Reference
---

# Configuration Reference

The sections of `~/.aethon/config.yaml`, field by field. A **missing or empty file
produces a fully-defaulted config**. The opt-in `capabilities`, `macos`, `lsp`,
`runtime_tools`, `session_recorder`, `ambient`, and `prompt` blocks are covered in the
conceptual guide (linked at the bottom). For that guide and the `${ENV_VAR}` resolution
rules, see **[Configuration](../getting-started/configuration.md)**.

## `model`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `provider` | str | `"openai"` | Model provider backend (openai, anthropic, ollama, bedrock, gemini, litellm, mistral, …), or `fake`/`echo` for an offline canned-reply backend (no network; used for tests). |
| `host` | str | `"http://localhost:11434"` | Base URL: the Ollama host, or an OpenAI-compatible endpoint when `provider: openai`. |
| `model_id` | str | `"gpt-4o"` | Model identifier. |
| `api_key` | str | `""` | API key for the provider. |
| `temperature` | float | `1.0` | Sampling temperature. |
| `top_p` | float | `0.95` | Nucleus sampling probability mass. |
| `top_k` | int | `40` | Top-k sampling cutoff. |
| `max_tokens` | int | `8192` | Max tokens to generate per response. |
| `region` | str | `"us-west-2"` | Provider region (e.g. for Bedrock-style backends). |
| `extra` | dict | `{}` | Arbitrary extra provider params. |

## `channels`

**`channels.cli`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the CLI channel. |

**`channels.webchat`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the web chat channel. |
| `port` | int | `18790` | Web chat listen port. |
| `host` | str | `"127.0.0.1"` | Bind address; loopback only by default. Set `0.0.0.0` to expose (also set `dashboard.auth_token`). |
| `allowed_origins` | list[str] | `[]` | Extra browser Origins accepted on WS upgrades (full origins, e.g. `https://chat.example.com`). Empty = same-host only. |

**`channels.telegram`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Telegram channel. |
| `token` | str | `""` | Telegram bot token. |
| `chat_id` | str | `""` | Default destination for proactive/outbound sends (scheduler, `send_message`, notifications). Reactive replies ignore it. |

**`channels.discord`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Discord channel. |
| `token` | str | `""` | Discord bot token. |
| `channel_id` | str | `""` | Default destination for proactive/outbound sends (channel id or user id for a DM). Reactive replies ignore it. |

**`channels.slack`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Slack channel. |
| `bot_token` | str | `""` | Slack bot token (`xoxb-…`). |
| `app_token` | str | `""` | Slack app-level token (`xapp-…`). |
| `channel` | str | `""` | Default destination for proactive/outbound sends (channel id `C…`, user id `U…`, or channel name). Reactive replies ignore it. |

**`channels.whatsapp`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the WhatsApp channel (experimental). |
| `chat` | str | `""` | Default destination for proactive/outbound sends (phone number / chat user id). Reactive replies ignore it. |

## `security`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `bypass_tool_consent` | bool | `true` | Run tools without the per-tool consent prompt (AETHON runs headless and has its own guardrails). Set `false` to restore per-tool prompts. |
| `workspace_only` | bool | `false` | When true, confine file tools to `~/.aethon/workspace`; when false (default), allow anywhere under `$HOME` except blocked system/credential paths. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Reserved; not currently enforced. Approval gating is configured in the `approval` section. |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Shell command substrings that are blocked. |
| `allowed_senders` | dict[str, list[str]] | `{}` | Per-channel allowlist of sender identifiers (empty list on a messaging bot = reject everyone). |
| `mark_untrusted_content` | bool | `true` | Wrap external-content tool results (`scraper`/`http_request`/`jsonrpc`/`use_github`) and webhook payloads in `[UNTRUSTED EXTERNAL CONTENT]` markers (honest marking, not an injection detector). |
| `sandbox` | str | `"none"` | `none` = shell runs on the host under the blocklist; `docker` = shell runs in a per-session container (fails closed if docker is unavailable). |
| `sandbox_image` | str | `"python:3.12-slim"` | Container image for the docker sandbox. |
| `sandbox_network` | str | `"none"` | `docker --network`; `none` = no host/network access. |
| `sandbox_memory` | str | `"512m"` | `docker --memory` cap. |
| `sandbox_cpus` | str | `"1.0"` | `docker --cpus` cap. |
| `sandbox_pids_limit` | int | `256` | `docker --pids-limit` cap. |
| `sandbox_timeout` | int | `60` | Seconds per shell command in the sandbox. |
| `sandbox_read_only` | bool | `true` | Read-only container rootfs (writable `/tmp` + the workspace mount). |

## `session`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `storage_dir` | str | `"~/.aethon/sessions"` | Directory where session state is stored. |
| `conversation_manager` | str | `"summarizing"` | Conversation manager strategy. |
| `summary_ratio` | float | `0.3` | Fraction of history to summarize when compacting. |
| `preserve_recent_messages` | int | `10` | Number of recent messages kept verbatim. |
| `compact_enabled` | bool | `false` | Replace old, large tool outputs in the model input with a compact marker (in-memory; the disk audit trail keeps the full output). Opt-in. |
| `compact_keep_last_n_turns` | int | `4` | Never compact the most recent N turns. |
| `compact_min_chars` | int | `800` | Only compact a result bigger than this. |
| `compact_trigger_chars` | int | `16000` | Run a compaction pass once this much old bulk piles up. |

## `memory`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable vector memory. |
| `embedding_provider` | str | `"ollama"` | Embedding provider (ollama, openai). |
| `embedding_model` | str | `"nomic-embed-text"` | Embedding model name. |
| `embedding_host` | str | `"http://localhost:11434"` | Embedding endpoint for the `ollama` provider (independent of the chat model host). |
| `embedding_api_key` | str | `""` | API key for the embedding provider. |
| `db_path` | str | `"~/.aethon/memory.sqlite"` | SQLite path for the vector store. |
| `auto_recall` | bool | `false` | Embed each incoming message and inject top-matching memories as a `## Recalled Memories` prompt layer (opt-in). |
| `recall_top_k` | int | `3` | Number of memories to recall. |
| `recall_min_score` | float | `0.0` | Only inject matches at/above this similarity. |
| `recall_max_chars` | int | `1500` | Max characters of recalled memory injected. |

## `multi_agent`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the multi-agent system. |
| `max_handoffs` | int | `10` | Max agent-to-agent handoffs. |
| `max_iterations` | int | `10` | Max iterations per run. |
| `execution_timeout` | float | `300.0` | Overall execution timeout (seconds). |
| `node_timeout` | float | `120.0` | Per-node timeout (seconds). |

## `sops`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable SOP execution. |
| `builtin_sops_enabled` | bool | `true` | Enable built-in SOPs. |

## `logging`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Attach a rotating file handler to the root logger (also captures third-party errors). |
| `level` | str | `"INFO"` | Log level for AETHON's own loggers. |
| `third_party_level` | str | `"WARNING"` | Log level for libraries (strands/uvicorn/aiogram/discord/slack). |

## `approval`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the interrupt-based approval hook. |
| `requires_approval` | list[str] | `["shell", "file_write", "manage_tools", "manage_specialists"]` | Action types requiring approval via this hook. |
| `timeout_seconds` | float | `120.0` | Seconds to wait for a human approval answer before denying. |

## `reliability`

All gates are **advisory by default** (they append feedback); `strict` flips them to hard gates.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `strict` | bool | `false` | Escalate findings from advisory feedback to hard gates. |
| `post_edit_verify` | bool | `true` | Run a verify command on edited files and append a `[Verify]` PASS/FAIL block. |
| `verify_cmd` | str | `""` | Verify command; `{paths}` is replaced with edited paths. Empty = auto-detect (`ruff check` on edited `*.py`). |
| `verify_timeout` | int | `30` | Seconds before a verify run is abandoned. |
| `completion_gate` | bool | `true` | Append a Definition-of-Done reminder when a success claim lacks verification evidence. |
| `anglicization_guard` | bool | `true` | Pause edits that replace existing Turkish text with English-only text (advisory). |
| `input_validator` | bool | `true` | Cancel malformed tool calls (empty shell command, missing file path). |

## `core_loop`

The autonomous core loop (work intake → plan → bounded executor → proof-of-work receipt). Every knob is **opt-in / off by default** unless noted.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `intake_enabled` | bool | `false` | Classify a clear unit of work and open it as a planned project instead of answering as chat. |
| `intake_work_phrases` | list[str] | (TR/EN phrases) | Phrases that force the work verdict. |
| `intake_chat_phrases` | list[str] | (TR/EN phrases) | Phrases that force the chat verdict (chat wins ties). |
| `plan_approval` | bool | `false` | When the executor runs, require user approval before executing a freshly-planned project. |
| `executor_enabled` | bool | `false` | Enable the bounded project executor. |
| `executor_max_iterations` | int | `20` | Hard cap on task turns per project run. |
| `executor_max_task_attempts` | int | `3` | Drop a task after N no-progress turns (durable). |
| `executor_stop_on_budget` | bool | `true` | Halt between tasks once the `budget` ceiling is breached. |
| `pulse_enabled` | bool | `true` | Send progress pulses to the origin channel while executing. |
| `pulse_every_n_tasks` | int | `3` | Send a pulse every N newly-completed tasks. |
| `receipt_enabled` | bool | `true` | Deliver a proof-of-work receipt when a run ends. |
| `capability_diet` | bool | `false` | Load heavy/domain tools only when the session needs them. |
| `dynamic_specialists` | bool | `false` | Expose `manage_specialists`; let the agent define + persist custom specialists. |
| `allow_powerful_specialists` | bool | `false` | Permit a dynamic specialist to hold a powerful tool (`shell`/`python_repl`/`file_write`/`editor`/`http_request`). |

## `telemetry`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the telemetry hook. |
| `max_history` | int | `10000` | Max telemetry events retained. |

## `budget`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `daily_usd` | float | `0.0` | Daily spend ceiling in USD; `0` = unlimited (measure only). Turns are warned near the ceiling and blocked once breached (also stops ambient/scheduler turns). |
| `warn_ratio` | float | `0.8` | Warn once spend crosses this fraction of the ceiling. |
| `pricing` | dict | `{}` | Override the built-in pricing table: USD per 1M tokens, `{model_substring: {"input": x, "output": y}}`. |

## `memory_guard`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the memory guard hook. |
| `custom_patterns` | list[str] | `[]` | Additional patterns the guard should catch. |

## `scheduler`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the scheduler. |
| `default_channel` | str | `"cli"` | Default channel for scheduled outputs. |
| `jobs` | dict | `{}` | Scheduled job definitions. |

## `dashboard`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the web dashboard. |
| `pixel_agents` | bool | `true` | Enable the pixel-agents visualization. |
| `auth_token` | str | `""` | Optional shared token; empty = no auth. Gates `/dashboard` and protected `/api/*` + `/ws/dashboard` via `?token=`, `Authorization: Bearer`, or the `aethon_dash` cookie. |

## `webhook`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the webhook endpoint. |
| `secret` | str | `""` | Shared secret to validate incoming webhooks (HMAC-SHA256). |

## `mcp`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable MCP server integration. |
| `servers` | list[dict] | `[]` | List of MCP server definitions. |

## `performance`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `model_warmup` | bool | `false` | Send a real model request on boot to reduce first-message latency (off by default; spends quota). |
| `session_cache_size` | int | `10` | Number of sessions cached in memory. |
| `embedding_cache_size` | int | `100` | Number of embeddings cached. |
| `max_tool_output_chars` | int | `12000` | Cap a single tool result so it can't overflow the context (`0` = off). |

## `repo_map`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Cache a compact `path → {purpose, symbols, hash}` summary of read files in `workspace/REPO_MAP.json` and inject a `## Repo Map` prompt layer (opt-in). |
| `max_files` | int | `100` | Cap the map to the newest N files. |
| `max_file_bytes` | int | `200000` | Skip files larger than this. |
| `max_snapshot_chars` | int | `2000` | Prompt-layer size cap. |

## `retention`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Prune session-reset backups + recordings at boot (`aethon doctor` reports disk usage). |
| `cleared_keep` | int | `10` | Newest `cleared/batch_*` kept per session (`0` = unlimited). |
| `recordings_keep` | int | `20` | Newest recording archives kept. |
| `recordings_max_age_days` | int | `0` | Age cap on recordings; `0` = no age cap. |

## `paths`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `workspace` | str | `"~/.aethon/workspace"` | Workspace root directory. |
| `sessions` | str | `"~/.aethon/sessions"` | Sessions directory. |
| `memory_db` | str | `"~/.aethon/memory.sqlite"` | Vector memory SQLite path. |
| `logs` | str | `"~/.aethon/logs"` | Logs directory. |
| `credentials` | str | `"~/.aethon/credentials"` | Credentials directory. |
| `recordings` | str | `"~/.aethon/recordings"` | Session recordings directory. |

:::note
`~` in path-valued fields is stored literally; it is expanded only for the config-file
path itself in `load()`/`write()`. Some values overlap intentionally (e.g.
`memory.db_path` and `paths.memory_db` both default to `~/.aethon/memory.sqlite`;
`session.storage_dir` and `paths.sessions` both `~/.aethon/sessions`).
:::

For the opt-in `capabilities`, `macos`, `lsp`, `runtime_tools`, `session_recorder`,
`ambient`, and `prompt` blocks, see **[Configuration](../getting-started/configuration.md#capabilities--runtime-features-opt-in)**
and **[Capabilities](../concepts/capabilities.md)**.
