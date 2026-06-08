---
id: configuration
title: Configuration Reference
sidebar_label: Configuration Reference
---

# Configuration Reference

Every section of `~/.aethon/config.yaml`, field by field. A **missing or empty file
produces a fully-defaulted config**. For the conceptual guide and `${ENV_VAR}`
resolution rules, see **[Configuration](../getting-started/configuration.md)**.

## `model`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `provider` | str | `"openai"` | Model provider backend (openai, anthropic, ollama, bedrock, gemini, litellm, mistral, …). |
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

**`channels.telegram`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Telegram channel. |
| `token` | str | `""` | Telegram bot token. |

**`channels.discord`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Discord channel. |
| `token` | str | `""` | Discord bot token. |

**`channels.slack`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the Slack channel. |
| `bot_token` | str | `""` | Slack bot token (`xoxb-…`). |
| `app_token` | str | `""` | Slack app-level token (`xapp-…`). |

**`channels.whatsapp`**

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the WhatsApp channel (experimental; no other fields). |

## `security`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `workspace_only` | bool | `false` | When true, confine file tools to `~/.aethon/workspace`; when false (default), allow anywhere under `$HOME` except blocked system/credential paths. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Reserved; not currently enforced. Approval gating is configured in the `approval` section. |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Shell command substrings that are blocked. |
| `allowed_senders` | dict[str, list[str]] | `{}` | Per-channel allowlist of sender identifiers. |

## `session`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `storage_dir` | str | `"~/.aethon/sessions"` | Directory where session state is stored. |
| `conversation_manager` | str | `"summarizing"` | Conversation manager strategy. |
| `summary_ratio` | float | `0.3` | Fraction of history to summarize when compacting. |
| `preserve_recent_messages` | int | `10` | Number of recent messages kept verbatim. |

## `memory`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable vector memory. |
| `embedding_provider` | str | `"ollama"` | Embedding provider (ollama, openai). |
| `embedding_model` | str | `"nomic-embed-text"` | Embedding model name. |
| `embedding_api_key` | str | `""` | API key for the embedding provider. |
| `db_path` | str | `"~/.aethon/memory.sqlite"` | SQLite path for the vector store. |

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

## `approval`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the interrupt-based approval hook. |
| `requires_approval` | list[str] | `["shell", "file_write"]` | Action types requiring approval via this hook. |

## `telemetry`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the telemetry hook. |
| `max_history` | int | `10000` | Max telemetry events retained. |

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
