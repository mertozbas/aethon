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
  embedding_model: nomic-embed-text   # Ollama embedding model
  db_path: ~/.aethon/memory.sqlite    # SQLite database path

# === Session ===
session:
  storage_dir: ~/.aethon/sessions     # Session files directory
  summary_ratio: 0.2                  # Conversation summary ratio (0.0-1.0)
  preserve_recent_messages: 10        # Last N messages are preserved

# === Channels ===
channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 18790
  telegram:
    enabled: false
    token: "${TELEGRAM_BOT_TOKEN}"    # Environment variable reference
  discord:
    enabled: false
    token: "${DISCORD_BOT_TOKEN}"
  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
  whatsapp:
    enabled: false

# === Security ===
security:
  bypass_tool_consent: true           # Headless: run tools without a per-tool prompt (default true)
  workspace_only: false               # If false, file tools may work under $HOME
                                      #   (system/credential paths stay blocked); default false
  blocked_commands:                   # Blocked commands
    - "rm -rf /"
    - "sudo "
    - "mkfs"
  allowed_senders:                    # Channel-based allowed users
    telegram: ["12345678"]
    discord: ["98765432"]

# === Approval Mechanism ===
approval:
  enabled: false                      # Require approval for dangerous tools
  requires_approval:                  # Tools requiring approval
    - shell
    - file_write

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
  default_channel: telegram           # Default channel for sending results
  jobs:                               # Pre-defined scheduled tasks
    morning-brief:
      cron: "0 9 * * 1-5"            # Weekdays at 9 AM
      sop_name: morning-brief
      channel: telegram

# === Dashboard ===
dashboard:
  enabled: true

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

# === Performance ===
performance:
  model_warmup: true                  # Model warm-up at startup
  session_cache_size: 10              # Max sessions kept in memory
  embedding_cache_size: 100           # LRU embedding cache size

# === Directories ===
paths:
  workspace: ~/.aethon/workspace
  sessions: ~/.aethon/sessions
  logs: ~/.aethon/logs
  memory_db: ~/.aethon/memory.sqlite
  credentials: ~/.aethon/credentials
```

---

## Config Details

### Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | str | `openai` | Model provider: `openai` (default), `anthropic`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral`, or `fake`/`echo` (offline test) |
| `model_id` | str | `gpt-4o` | Model name |
| `api_key` | str | `${OPENAI_API_KEY}` | API key for the provider (OpenAI / Anthropic / etc.); not needed for Ollama |
| `host` | str | — | Base URL of an OpenAI-compatible endpoint (vLLM / LM Studio / LocalAI / …), or the Ollama server address (e.g. `http://localhost:11434`) |
| `temperature` | float | `1.0` | Sampling temperature (0.0-2.0) |
| `max_tokens` | int | `8192` | Max output token count |

`bedrock` / `gemini` / `litellm` / `mistral` each require their own SDK installed
(`boto3` / `google-genai` / `litellm` / `mistralai`, respectively).

### Memory

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Whether long-term memory is active |
| `embedding_model` | str | `nomic-embed-text` | Embedding model |
| `db_path` | str | `~/.aethon/memory.sqlite` | SQLite database path |

### Channels

For each channel:

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Whether the channel is active |
| `token` | str | Bot token (supports environment variables: `${VAR}`) |
| `port` | int | Listening port for WebChat |

### Security

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bypass_tool_consent` | bool | `true` | Run tools headlessly without a per-tool consent prompt |
| `workspace_only` | bool | `false` | When `false`, file tools may operate anywhere under `$HOME`; system and credential paths remain blocked. Set `true` to confine file tools to the workspace |
| `blocked_commands` | list[str] | (see example) | Shell command prefixes that are always refused |
| `allowed_senders` | dict | `{}` | Per-channel allow-lists of user IDs |

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
| `default_channel` | str | `telegram` | Default result channel |
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
| `model_warmup` | bool | `true` | Model warm-up at startup (reduces first request latency) |
| `session_cache_size` | int | `10` | Max sessions kept in memory (LRU) |
| `embedding_cache_size` | int | `100` | Embedding LRU cache size |

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
