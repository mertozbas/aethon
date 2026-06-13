# AETHON — Configuration Reference

> Description of all settings in the `~/.aethon/config.yaml` file.

---

## Full Config Example

```yaml
# === Model ===
model:
  provider: openai                    # openai | anthropic | ollama | bedrock | gemini | litellm | mistral | fake
  model_id: gpt-4o                    # default model id
  api_key: ${OPENAI_API_KEY}          # official OpenAI API key
  # host: https://your-endpoint/v1    # OR any OpenAI-compatible base URL (vLLM / LM Studio / LocalAI / …)
  temperature: 1.0                    # Sampling temperature (0.0-2.0)
  max_tokens: 8192                    # Max output token count
  # provider: ollama                  # fully-local alternative (no API key):
  # model_id: qwen3-coder-next
  # host: http://localhost:11434      # Ollama server address

# === Memory ===
memory:
  enabled: true
  embedding_provider: ollama          # ollama | openai
  embedding_model: nomic-embed-text   # Ollama embedding model
  embedding_host: http://localhost:11434  # Embedding endpoint for the ollama provider
  db_path: ~/.aethon/memory.sqlite    # SQLite database path
  # Automatic recall (opt-in, default off): embed the incoming message and
  # inject the top matching long-term memories as a prompt layer.
  auto_recall: false
  recall_top_k: 3
  recall_min_score: 0.0
  recall_max_chars: 1500

# === Session ===
session:
  storage_dir: ~/.aethon/sessions     # Session files directory
  conversation_manager: summarizing   # Conversation manager strategy
  summary_ratio: 0.3                  # Conversation summary ratio (0.0-1.0)
  preserve_recent_messages: 10        # Last N messages are preserved
  # History compaction (opt-in, default off): replace old, large tool outputs
  # in the model input with a compact marker (disk keeps the full audit trail).
  compact_enabled: false
  compact_keep_last_n_turns: 4
  compact_min_chars: 800
  compact_trigger_chars: 16000

# === Channels ===
channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 18790
    host: 127.0.0.1                   # Bind address; set 0.0.0.0 to expose on a network/container
    allowed_origins: []               # Extra browser Origins accepted on WS upgrades
  telegram:
    enabled: false
    token: "${TELEGRAM_BOT_TOKEN}"    # Environment variable reference
    chat_id: ""                       # Default destination for proactive/outbound sends
  discord:
    enabled: false
    token: "${DISCORD_BOT_TOKEN}"
    channel_id: ""                    # Default destination for proactive/outbound sends
  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
    channel: ""                       # Default destination for proactive/outbound sends
  whatsapp:
    enabled: false
    chat: ""                          # Default destination for proactive/outbound sends

# === Security ===
security:
  bypass_tool_consent: true           # Headless: run tools without a per-tool prompt (default true)
  workspace_only: false               # If false, file tools may work under $HOME
                                      #   (system/credential paths stay blocked); default false
  blocked_commands:                   # Blocked command prefixes (always refused)
    - "rm -rf /"
    - "sudo"
    - "mkfs"
  allowed_senders:                    # Channel-based allowed users
    telegram: ["12345678"]
    discord: ["98765432"]
  mark_untrusted_content: true        # Wrap external-content tool results in [UNTRUSTED EXTERNAL CONTENT] markers
  # Execution sandbox for the `shell` tool (default: none = host under the blocklist).
  sandbox: none                       # none | docker
  sandbox_image: python:3.12-slim
  sandbox_network: none               # docker --network; none = no host/network access
  sandbox_memory: 512m                # docker --memory cap
  sandbox_cpus: "1.0"                 # docker --cpus cap
  sandbox_pids_limit: 256             # docker --pids-limit cap
  sandbox_timeout: 60                 # seconds per shell command
  sandbox_read_only: true             # read-only container rootfs (writable /tmp + workspace)

# === Approval Mechanism ===
approval:
  enabled: false                      # Require approval for dangerous tools
  requires_approval:                  # Tools requiring approval
    - shell
    - file_write
    - manage_tools
    - manage_specialists
  timeout_seconds: 120.0              # Seconds to wait for a human approval answer before denying

# === Multi-Agent ===
multi_agent:
  enabled: true

# === SOP ===
sops:
  enabled: true
  builtin_sops_enabled: true          # Load built-in SOPs

# === Telemetry ===
telemetry:
  enabled: true
  max_history: 10000                  # Max metric history

# === Memory Protection ===
memory_guard:
  enabled: true
  custom_patterns:                    # Additional sensitive information patterns
    - "internal_secret=\\S+"

# === Scheduler ===
scheduler:
  enabled: true
  default_channel: cli                # Default channel for sending results (cli is enabled by default)
  jobs:                               # Pre-defined scheduled tasks
    daily-brief:
      cron: "0 9 * * 1-5"            # Weekdays at 9 AM
      sop_name: daily-brief
      channel: telegram               # an enabled channel for this job's output

# === Dashboard ===
dashboard:
  enabled: true
  pixel_agents: true                  # Render agents in the pixel-art dashboard view
  auth_token: ""                      # Shared token; set before exposing on a network (gates all /api/* and /ws/dashboard)

# === Webhook ===
webhook:
  enabled: true
  secret: ""                          # HMAC-SHA256 validation key (empty = none)

# === MCP ===
mcp:
  enabled: false
  servers:
    - command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]

# === Logging ===
logging:
  enabled: true                       # Rotating file handler on the root logger
  level: INFO                         # AETHON's own loggers
  third_party_level: WARNING          # libraries (strands/uvicorn/aiogram/discord/slack)

# === Budget (token spend ceiling) ===
budget:
  daily_usd: 0.0                      # Daily spend ceiling in USD; 0 = unlimited (measure only)
  warn_ratio: 0.8                     # Warn once spend crosses this fraction of the ceiling
  pricing: {}                         # Override the built-in pricing table (USD per 1M tokens)

# === Reliability (verification backstop) ===
reliability:
  strict: false                       # Escalate advisory findings to hard gates
  post_edit_verify: true              # Run a verify command on edited files; append a [Verify] block
  verify_cmd: ""                      # Verify command ({paths} -> edited paths); empty = auto-detect (ruff check on *.py)
  verify_timeout: 30                  # Seconds before a verify run is abandoned
  completion_gate: true               # Append a Definition-of-Done reminder on unverified success claims
  anglicization_guard: true           # Pause edits that replace existing Turkish text with English-only text
  input_validator: true               # Cancel malformed tool calls (empty shell command, missing file path)

# === Core Loop (autonomous intake -> plan -> execute -> receipt) ===
core_loop:
  intake_enabled: false               # Classify a clear unit of work and open it as a planned project
  plan_approval: false                # Require user approval before executing a freshly-planned project
  executor_enabled: false             # Enable the bounded project executor
  executor_max_iterations: 20         # Hard cap on task turns per project run
  executor_max_task_attempts: 3       # Drop a task after N no-progress turns
  executor_stop_on_budget: true       # Halt between tasks once the budget ceiling is breached
  pulse_enabled: true                 # Send progress pulses to the origin channel while executing
  pulse_every_n_tasks: 3              # Send a pulse every N newly-completed tasks
  receipt_enabled: true               # Deliver a proof-of-work receipt when a run ends
  capability_diet: false              # Load heavy/domain tools only when the session needs them
  dynamic_specialists: false          # Expose manage_tools/manage_specialists; let the agent define custom specialists
  allow_powerful_specialists: false   # Permit a dynamic specialist to hold a powerful tool

# === Retention (disk cleanup) ===
retention:
  enabled: true                       # Prune session-reset backups + recordings at boot
  cleared_keep: 10                    # Newest cleared/batch_* kept per session (0 = unlimited)
  recordings_keep: 20                 # Newest recording archives kept
  recordings_max_age_days: 0          # Age cap on recordings; 0 = no age cap

# === Repo Map (file-summary cache) ===
repo_map:
  enabled: false                      # Cache a path -> purpose/symbols/hash summary; inject a ## Repo Map layer
  max_files: 100                      # Cap the map to the newest N files
  max_file_bytes: 200000              # Skip files larger than this
  max_snapshot_chars: 2000            # Prompt-layer size cap

# === Runtime Tools (manage_tools) ===
runtime_tools:
  enabled: false                      # Gate registration of the manage_tools dynamic-tool loader
  allow_create: false                 # Permit create/fetch (validated in a subprocess sandbox)
  allow_install: false                # Permit add/reload (auto-installing missing packages)
  sandbox_timeout: 30
  cache_dir: ~/.aethon/runtime_tools_cache

# === Performance ===
performance:
  model_warmup: false                 # Model warm-up at startup (off by default — spends model quota every boot)
  session_cache_size: 10              # Max sessions kept in memory
  embedding_cache_size: 100           # LRU embedding cache size
  max_tool_output_chars: 12000        # Cap text a single tool result feeds back to the model (0 disables)

# === Directories ===
paths:
  workspace: ~/.aethon/workspace
  sessions: ~/.aethon/sessions
  logs: ~/.aethon/logs
  memory_db: ~/.aethon/memory.sqlite
  credentials: ~/.aethon/credentials
  recordings: ~/.aethon/recordings
```

---

## Config Details

### Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | str | `openai` | Model provider: `openai` (default), `anthropic`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral`, or `fake`/`echo` (offline test) |
| `model_id` | str | `gpt-4o` | Model name |
| `api_key` | str | `${OPENAI_API_KEY}` | API key for the provider (OpenAI / Anthropic / etc.); not needed for Ollama |
| `host` | str | — | Base URL of an OpenAI-compatible endpoint (vLLM / LM Studio / LocalAI / …), or the Ollama server address (e.g. `http://localhost:11434`). The default (`http://localhost:11434`) is treated as "unset" by the `openai` provider, which then uses the official API |
| `temperature` | float | `1.0` | Sampling temperature (0.0-2.0) |
| `top_p` | float | `0.95` | Nucleus-sampling cutoff |
| `top_k` | int | `40` | Top-k sampling cutoff |
| `max_tokens` | int | `8192` | Max output token count |
| `region` | str | `us-west-2` | AWS region (for the `bedrock` provider) |
| `extra` | dict | `{}` | Free-form provider-specific options passed through to the model |

`bedrock` / `gemini` / `litellm` / `mistral` each require their own SDK installed
(`boto3` / `google-genai` / `litellm` / `mistralai`, respectively).

### Memory

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether long-term memory is active |
| `embedding_provider` | str | `ollama` | Embedding backend: `ollama` (local) or `openai` |
| `embedding_model` | str | `nomic-embed-text` | Embedding model |
| `embedding_host` | str | `http://localhost:11434` | Embedding endpoint for the `ollama` provider (independent of the chat model host) |
| `embedding_api_key` | str | `""` | API key for the `openai` embedding provider |
| `db_path` | str | `~/.aethon/memory.sqlite` | SQLite database path |
| `auto_recall` | bool | `false` | Opt-in: embed each incoming message and inject top-matching memories as a `## Recalled Memories` prompt layer |
| `recall_top_k` | int | `3` | Number of memories to recall |
| `recall_min_score` | float | `0.0` | Only inject matches at/above this similarity |
| `recall_max_chars` | int | `1500` | Max characters of recalled memory injected |

### Channels

For each channel:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | (varies) | Whether the channel is active (CLI/WebChat on; Telegram/Discord/Slack/WhatsApp off) |
| `token` | str | `""` | Bot token for Telegram/Discord (supports environment variables: `${VAR}`) |
| `port` | int | `18790` | Listening port for WebChat |

WebChat (`channels.webchat`) adds:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | str | `127.0.0.1` | Bind address. Loopback by default; set `0.0.0.0` to expose on a network or inside a container — set `dashboard.auth_token` first |
| `allowed_origins` | list[str] | `[]` | Extra browser Origins accepted on the WebSocket upgrades (full origins, e.g. `https://chat.example.com`). Empty = same-host only |

Each messaging channel carries a default destination for **proactive/outbound** sends
(scheduler, notifications); reactive replies always answer the inbound chat and ignore it:

| Channel | Field | Default | Description |
|---------|-------|---------|-------------|
| `telegram` | `chat_id` | `""` | Default outbound chat/user id |
| `discord` | `channel_id` | `""` | Default outbound channel or user (DM) id |
| `slack` | `channel` | `""` | Default outbound channel id (`C...`), user id (`U...`), or channel name |
| `whatsapp` | `chat` | `""` | Default outbound phone number / chat user id |

Slack uses two tokens (`bot_token` + `app_token`) rather than a single `token`.

### Security

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bypass_tool_consent` | bool | `true` | Run tools headlessly without a per-tool consent prompt |
| `workspace_only` | bool | `false` | When `false`, file tools may operate anywhere under `$HOME`; system and credential paths remain blocked. Set `true` to confine file tools to the workspace |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Shell command prefixes that are always refused |
| `allowed_senders` | dict | `{}` | Per-channel allow-lists of user IDs |
| `mark_untrusted_content` | bool | `true` | Wrap results from external-content tools (scraper, github, jsonrpc) and webhook payloads in `[UNTRUSTED EXTERNAL CONTENT]` markers so the model treats them as data, not instructions (honest marking, not an injection detector) |
| `sandbox` | str | `none` | Execution sandbox for the `shell` tool: `none` = host under the blocklist; `docker` = per-session container (fails closed if docker is unavailable) |
| `sandbox_image` | str | `python:3.12-slim` | Container image for the docker sandbox |
| `sandbox_network` | str | `none` | `docker --network`; `none` = no host/network access |
| `sandbox_memory` | str | `512m` | `docker --memory` cap |
| `sandbox_cpus` | str | `1.0` | `docker --cpus` cap |
| `sandbox_pids_limit` | int | `256` | `docker --pids-limit` cap |
| `sandbox_timeout` | int | `60` | Seconds per shell command in the sandbox |
| `sandbox_read_only` | bool | `true` | Read-only container rootfs (writable `/tmp` + workspace mount) |

See the [SECURITY.md](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) for the
Docker sandbox, untrusted-content marking, and the network-bind security model.

### Telemetry

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether telemetry collection is active |
| `max_history` | int | `10000` | Max number of metrics kept in memory |

### Memory Guard

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether sensitive information protection is active |
| `custom_patterns` | list[str] | `[]` | Additional regex patterns |

**Default blocked patterns:**
- API keys (`api_key=...`)
- Passwords (`password=...`)
- Tokens (`secret=...`, `token=...`)
- SSH keys (`ssh-rsa ...`)
- Private key blocks (`-----BEGIN ... PRIVATE KEY-----`)
- Credit card numbers
- SSN numbers

### Scheduler

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether the scheduler is active |
| `default_channel` | str | `cli` | Default result channel (CLI is enabled by default; Telegram is opt-in) |
| `jobs` | dict | `{}` | Pre-defined cron jobs |

**Cron format:** `minute hour day month dayOfWeek`

| Example | Meaning |
|---------|---------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `30 18 * * 5` | Friday at 6:30 PM |
| `0 0 1 * *` | First of every month at midnight |

### Performance

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_warmup` | bool | `false` | Model warm-up at startup. Off by default because it spends a real model request (API credits/quota) on every boot; opt in for lower first-message latency |
| `session_cache_size` | int | `10` | Max sessions kept in memory (LRU) |
| `embedding_cache_size` | int | `100` | Embedding LRU cache size |
| `max_tool_output_chars` | int | `12000` | Cap on how much text a single tool result feeds back to the model (`0` disables; ~12000 chars ≈ 3k tokens) |

### Session

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `storage_dir` | str | `~/.aethon/sessions` | Session files directory |
| `conversation_manager` | str | `summarizing` | Conversation-manager strategy |
| `summary_ratio` | float | `0.3` | Conversation summary ratio (0.0-1.0) |
| `preserve_recent_messages` | int | `10` | Last N messages always preserved |
| `compact_enabled` | bool | `false` | Opt-in: replace old, large tool outputs in the model input with a compact marker (in-memory; disk keeps the full audit trail) |
| `compact_keep_last_n_turns` | int | `4` | Never compact the most recent N turns |
| `compact_min_chars` | int | `800` | Only compact a result bigger than this |
| `compact_trigger_chars` | int | `16000` | Run a compaction pass once this much old bulk piles up |

### Approval

Interrupt-based approval hook (disabled by default).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Require human approval before the listed tools run |
| `requires_approval` | list[str] | `["shell", "file_write", "manage_tools", "manage_specialists"]` | Tools that pause for approval |
| `timeout_seconds` | float | `120.0` | Seconds to wait for a human answer before denying (fails closed) |

### Dashboard

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether the web dashboard is served |
| `pixel_agents` | bool | `true` | Render agents in the pixel-art dashboard view |
| `auth_token` | str | `""` | Shared token. Empty = no auth (fine for the default localhost bind). When set, it gates **all** `/api/*` and `/ws/dashboard` access (pass via `?token=...`, an `Authorization: Bearer` header, or the `aethon_dash` cookie). **Required before binding to a non-loopback host.** |

### Logging

Rotating file handler on the root logger (so third-party errors reach the log too).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Attach the rotating file handler |
| `level` | str | `INFO` | Log level for AETHON's own loggers |
| `third_party_level` | str | `WARNING` | Log level for libraries (strands/uvicorn/aiogram/discord/slack) |

### Budget (token spend ceiling)

Token usage is measured per turn; with `daily_usd` set, turns are warned near the ceiling
and blocked once it is breached (this also stops ambient/scheduler turns).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `daily_usd` | float | `0.0` | Daily spend ceiling in USD; `0` = unlimited (measure only) |
| `warn_ratio` | float | `0.8` | Warn once spend crosses this fraction of the ceiling |
| `pricing` | dict | `{}` | Override the built-in pricing table (USD per 1M tokens): `{model_substring: {"input": x, "output": y}}` |

### Reliability

A verification backstop. All gates are **advisory** by default (they append feedback);
`strict` flips them to hard gates.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strict` | bool | `false` | Escalate findings from advisory feedback to hard gates |
| `post_edit_verify` | bool | `true` | Run a verify command on edited files and append a `[Verify]` PASS/FAIL block |
| `verify_cmd` | str | `""` | Verify command; `{paths}` is replaced with edited paths. Empty = auto-detect (`ruff check` on edited `*.py`) |
| `verify_timeout` | int | `30` | Seconds before a verify run is abandoned |
| `completion_gate` | bool | `true` | Append a Definition-of-Done reminder when a success claim lacks verification evidence |
| `anglicization_guard` | bool | `true` | Pause edits that replace existing Turkish text with English-only text (advisory) |
| `input_validator` | bool | `true` | Cancel malformed tool calls (empty shell command, missing file path) |

### Core Loop

The autonomous core loop (intake → plan → execute → receipt). Every knob is opt-in / off
by default unless noted; the runaway guards (`executor_max_iterations`,
`executor_max_task_attempts`, `executor_stop_on_budget`) are load-bearing.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `intake_enabled` | bool | `false` | Classify a clear unit of work and open it as a planned project instead of answering as chat |
| `intake_work_phrases` | list[str] | (TR/EN phrases) | Phrases that force the "work" verdict |
| `intake_chat_phrases` | list[str] | (TR/EN phrases) | Phrases that force the "chat" verdict (chat wins ties) |
| `plan_approval` | bool | `false` | Require user approval before executing a freshly-planned project |
| `executor_enabled` | bool | `false` | Enable the bounded project executor |
| `executor_max_iterations` | int | `20` | Hard cap on task turns per project run |
| `executor_max_task_attempts` | int | `3` | Drop a task after N no-progress turns (durable) |
| `executor_stop_on_budget` | bool | `true` | Halt between tasks once the budget ceiling is breached |
| `pulse_enabled` | bool | `true` | Send progress pulses to the origin channel while executing |
| `pulse_every_n_tasks` | int | `3` | Send a pulse every N newly-completed tasks |
| `receipt_enabled` | bool | `true` | Deliver a proof-of-work receipt when a run ends |
| `capability_diet` | bool | `false` | Load heavy/domain tools only when the session needs them |
| `dynamic_specialists` | bool | `false` | Expose `manage_specialists`; let the agent define + persist custom specialists |
| `allow_powerful_specialists` | bool | `false` | Permit a dynamic specialist to hold a powerful tool (shell/file_write/editor/…) |

### Retention

Disk cleanup at boot (`aethon doctor` reports disk usage). `0` = unlimited.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Prune session-reset backups + recordings at boot |
| `cleared_keep` | int | `10` | Newest `cleared/batch_*` kept per session (`0` = unlimited) |
| `recordings_keep` | int | `20` | Newest recording archives kept |
| `recordings_max_age_days` | int | `0` | Age cap on recordings; `0` = no age cap |

### Repo Map

Caches a compact `path → {purpose, symbols, hash}` summary of read files in
`workspace/REPO_MAP.json` and injects a `## Repo Map` prompt layer. Off by default.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable the repo-map cache + prompt layer |
| `max_files` | int | `100` | Cap the map to the newest N files |
| `max_file_bytes` | int | `200000` | Skip files larger than this |
| `max_snapshot_chars` | int | `2000` | Prompt-layer size cap |

### Runtime Tools

Dynamic tool loading via the `manage_tools` tool. Off by default; the security hook
enforces these per action.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Gate registration of `manage_tools` |
| `allow_create` | bool | `false` | Permit create/fetch (validated in a subprocess sandbox) |
| `allow_install` | bool | `false` | Permit add/reload (auto-installing missing packages) |
| `sandbox_timeout` | int | `30` | Seconds before a create/fetch sandbox run is abandoned |
| `cache_dir` | str | `~/.aethon/runtime_tools_cache` | Where fetched/created tools are cached |

---

## Environment Variable Support

Environment variable references in the form `${VAR_NAME}` can be used in the config:

```yaml
channels:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"
```

AETHON automatically resolves `${}` values when loading the config.

---

## Workspace Files

| File | Location | Purpose |
|------|----------|---------|
| `SOUL.md` | `~/.aethon/workspace/SOUL.md` | Agent personality and behavior rules |
| `TOOLS.md` | `~/.aethon/workspace/TOOLS.md` | User preferences |
| `CONTEXT.md` | `~/.aethon/workspace/CONTEXT.md` | Current context (automatically updated) |
| `sops/` | `~/.aethon/workspace/sops/` | Custom SOP files |
| `LEARNINGS.md` | `~/.aethon/workspace/LEARNINGS.md` | Durable learnings injected into the prompt |
| `TASKS.json` | `~/.aethon/workspace/TASKS.json` | Task ledger (open/closed tasks) |
| `SCHEDULE.json` | `~/.aethon/workspace/SCHEDULE.json` | Persisted scheduler jobs |
| `REPO_MAP.json` | `~/.aethon/workspace/REPO_MAP.json` | File-summary cache (when `repo_map.enabled`) |
| `specialists/` | `~/.aethon/workspace/specialists/` | Custom specialist definitions (when `core_loop.dynamic_specialists`) |

Recordings (when `session_recorder.enabled`) are written to `~/.aethon/recordings/`
(see `paths.recordings`).
