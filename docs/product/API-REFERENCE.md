# AETHON — API Reference

> All HTTP endpoints, WebSocket protocols, webhook integrations, and agent tools.

---

## 1. WebChat Endpoints

AETHON listens on `http://127.0.0.1:18790` by default.

### 1.1 WebChat UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | WebChat interface (HTML) |

The WebChat UI is served at the root. The monitoring dashboard lives at `/dashboard`
(see section 2.1).

**Example:**
```
GET http://127.0.0.1:18790/
```

### 1.2 WebSocket Chat

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws/chat` | WebSocket | Real-time chat |

**Connection:**
```javascript
const ws = new WebSocket("ws://127.0.0.1:18790/ws/chat");
```

**Sending a Message:**
```json
"Merhaba, bugun ne yapacagiz?"
```

**Receiving a Response:**
```json
"Merhaba! Sana nasil yardimci olabilirim?"
```

The WebSocket connection is text-based. The client sends plain text, and the server returns plain text.

---

## 2. Dashboard API

When the dashboard is active (`dashboard.enabled: true`), the following endpoints are available.

### 2.0 Authentication

By default AETHON binds to `127.0.0.1` and the API is open to the local user. Setting
`dashboard.auth_token` turns on deny-by-default authentication for the whole shared app:
every HTTP route — all `/api/*`, the dashboard, FastAPI docs, and unknown paths — requires
the token, returning `401` when it is missing or invalid.

The token may be supplied three ways:

- `?token=<token>` query parameter,
- `Authorization: Bearer <token>` header,
- `aethon_dash` cookie (set automatically after a successful `/dashboard?token=...` load).

WebSocket endpoints (`/ws/chat`, `/ws/dashboard`) gate themselves before accepting the
upgrade: they validate the `Origin` header against `channels.webchat.allowed_origins` and
then the token, closing with code `1008` on failure.

Public exceptions (always reachable): `/` (WebChat UI), `/health`, `/dashboard/static/*`
(SPA assets), and `/webhook/*` (self-authenticating via HMAC — see section 3.3).

The token is **mandatory** before binding to a non-loopback host such as `0.0.0.0`; `aethon
start` refuses such a bind unless `dashboard.auth_token` is set, or `--insecure-bind` is
passed to override (only behind a trusted reverse proxy). See the root
[SECURITY.md](https://github.com/mertozbas/aethon/blob/main/SECURITY.md).

### 2.1 Dashboard UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard` | GET | Monitoring panel (HTML) |

**Example:**
```
GET http://127.0.0.1:18790/dashboard
```

Glassmorphism + cyberpunk neon themed monitoring panel. Displays sessions, memory, telemetry, and scheduled tasks. Auto-refreshes every 5 seconds.

### 2.2 Session List

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | GET | List active sessions |

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "telegram:12345678",
      "agent_name": "AETHON"
    }
  ],
  "count": 1
}
```

### 2.3 Memory Statistics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory` | GET | Memory status and recent records |

**Response:**
```json
{
  "enabled": true,
  "count": 42,
  "entries": [
    {
      "id": 1,
      "content": "Python projesi icin asyncio kullan",
      "category": "preference",
      "created_at": "2026-03-12T10:30:00"
    }
  ]
}
```

### 2.4 Memory Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memory/search` | POST | Semantic memory search |

**Request:**
```json
{
  "query": "Python tercihleri"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "content": "Python projesi icin asyncio kullan",
      "category": "preference",
      "similarity": 0.89
    }
  ]
}
```

### 2.5 Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET | Current system configuration |

**Response:**
```json
{
  "model": {
    "provider": "openai",
    "model_id": "gpt-4o",
    "host": "http://localhost:11434",
    "temperature": 1.0,
    "max_tokens": 8192
  },
  "memory": { "enabled": true, "..." : "..." },
  "channels": { "..." : "..." }
}
```

Values reflect the configured provider; the snippet above shows the built-in defaults
(`openai` / `gpt-4o`).

### 2.6 Scheduled Tasks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scheduler/jobs` | GET | Scheduled task list |

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "morning-brief",
      "sop_name": "morning-brief",
      "cron": "0 9 * * 1-5",
      "channel": "telegram",
      "next_run": "2026-03-13 09:00:00"
    }
  ]
}
```

### 2.7 Telemetry

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telemetry` | GET | Telemetry summary and recent metrics |

**Response:**
```json
{
  "enabled": true,
  "summary": {
    "total_tool_calls": 156,
    "total_model_calls": 89,
    "error_count": 2,
    "avg_tool_duration": 0.45,
    "avg_model_duration": 3.21,
    "tool_success_rate": 0.987,
    "model_success_rate": 1.0
  },
  "metrics": [
    {
      "type": "tool",
      "name": "shell",
      "duration": 0.32,
      "status": "success",
      "timestamp": "2026-03-12T14:30:15"
    }
  ]
}
```

### 2.8 Live Dashboard Stream

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws/dashboard` | WebSocket | Real-time dashboard updates (sessions, memory, telemetry topics) |

A single WebSocket multiplexes the dashboard's live topics rather than exposing one socket
per metric. It is **gated before accept**: the connection validates the `Origin` header
against `channels.webchat.allowed_origins` and, when `dashboard.auth_token` is set, the
token (`?token=`, `Authorization: Bearer`, or the `aethon_dash` cookie). On failure the
socket is closed with code `1008`.

**Connection:**
```javascript
const ws = new WebSocket("ws://127.0.0.1:18790/ws/dashboard");
ws.onmessage = (e) => {
  const update = JSON.parse(e.data);
  console.log(update.topic, update);
};
```

There is no fixed-interval push; the server emits updates as dashboard state changes.

### 2.9 Additional Dashboard Endpoints

The dashboard SPA is backed by further REST routes on the same app (all subject to the
section 2.0 token gate when `dashboard.auth_token` is set):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config/schema` | GET | JSON schema of the full configuration surface |
| `/api/sessions/{session_id}` | GET | Detail for a single active session |
| `/api/memory/stats` | GET | Memory store statistics |
| `/api/memory` | POST | Add a memory record |
| `/api/memory/{memory_id}` | DELETE | Delete a memory record |
| `/api/sops` | GET | List available SOPs |
| `/api/sops/{name}` | GET / PUT / DELETE | Read, create/update, or delete a custom SOP |
| `/api/agents/active` | GET | Currently running agents / specialists |
| `/api/agents/history` | GET | Recent agent activity |

When session recording is enabled (`session_recorder.enabled`), the recording browse and
replay tree is also served (see [CAPABILITIES.md](../CAPABILITIES.md)):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions/recordings` | GET | List recorded session ZIPs |
| `/api/sessions/recordings/{zip}` | GET | Recording metadata |
| `/api/sessions/recordings/{zip}/events` | GET | Recorded event timeline |
| `/api/sessions/recordings/{zip}/snapshots` | GET | State snapshots |
| `/api/sessions/recordings/{zip}/replay/{snapshot_id}` | POST | Replay preview from a snapshot (never mutates the live agent) |

---

## 3. Webhook Endpoints

When webhooks are active (`webhook.enabled: true`), external message and SOP triggering is possible.

### 3.1 Channel-Based Webhook

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /webhook/{channel}` | POST | Send a message to the specified channel |

**Example:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"text": "Merhaba AETHON!"}'
```

**Response:**
```json
{
  "status": "ok",
  "response": "Merhaba! Nasil yardimci olabilirim?"
}
```

### 3.2 SOP Trigger

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /webhook/trigger` | POST | Run an SOP and send the result to a channel |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | No | Message text |
| `sop_name` | string | No | Name of the SOP to run |
| `channel` | string | No | Channel to send the result to |
| `recipient` | string | No | Recipient ID |

**Example — SOP Trigger:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "sop_name": "morning-brief",
    "text": "Bugunun ozeti",
    "channel": "telegram",
    "recipient": "12345678"
  }'
```

**Example — Plain Message:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"text": "Proje durumu nedir?"}'
```

**Response:**
```json
{
  "status": "ok",
  "response": "Proje durumu: 3 acik gorev, 2 tamamlanan..."
}
```

### 3.3 HMAC-SHA256 Validation

When a webhook secret is set (`webhook.secret` in config), the `X-Aethon-Signature` header is required on all requests.

**Creating a Signature:**
```python
import hashlib, hmac

secret = "benim-gizli-anahtarim"
body = b'{"text": "Merhaba"}'
signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

# Header: X-Aethon-Signature: <signature>
```

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -H "X-Aethon-Signature: a1b2c3d4e5..." \
  -d '{"text": "Guvenli mesaj"}'
```

If the secret is empty (`""`), validation is disabled.

---

## 4. Agent Tools

All tools used by the AETHON agent. The agent uses these tools automatically during message processing.

### 4.1 Built-in Tools

These six tools are always registered:

| Tool | Description |
|------|-------------|
| `file_read` | Read a file |
| `file_write` | Write a file |
| `editor` | Edit a file (diff-based) |
| `shell` | Run a command (swapped for a containerized shell when `security.sandbox: docker`) |
| `think` | Internal thought (planning) |
| `current_time` | Current date/time |

HTTP access is not a built-in tool; it is provided by the optional, config-gated
capability tools (`scraper`, `jsonrpc`, `use_github`) — see section 4.7 and
[CAPABILITIES.md](../CAPABILITIES.md).

### 4.2 Specialist Delegation Tools

Registered when the specialist factory is active.

| Tool | Signature | Description |
|------|-----------|-------------|
| `ask_coder` | `ask_coder(task)` | Delegate a coding task to the coder specialist |
| `ask_researcher` | `ask_researcher(query)` | Delegate a research task to the researcher |
| `ask_analyst` | `ask_analyst(data_task)` | Delegate analysis/computation to the analyst |
| `ask_planner` | `ask_planner(planning_task)` | Delegate planning to the planner |
| `ask_scout` | `ask_scout(query)` | "Read many, return little" investigation — the scout reads the cited sources and returns only a concise conclusion, keeping bulk output out of the main context |
| `ask_specialist` | `ask_specialist(specialist_name, task)` | Delegate to any specialist by name, including custom ones |
| `manage_specialists` | `manage_specialists(...)` | Create/list/remove dynamic specialists. **Opt-in** via `core_loop.dynamic_specialists`; powerful tools require `core_loop.allow_powerful_specialists` (see [CAPABILITIES.md](../CAPABILITIES.md)) |

**How It Works:** The main agent delegates to the appropriate specialist, which completes
the task with its own tools and returns the result.

### 4.3 Memory Management Tool

| Tool | File | Description |
|------|------|-------------|
| `manage_memory` | `tools/memory_tool.py` | Manage long-term memory |

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | str | `store`, `search`, `list`, `forget` |
| `content` | str | Content to add to memory (for store) |
| `category` | str | Category label (for store, optional) |
| `query` | str | Search query (for search) |
| `memory_id` | int | Record ID to delete (for forget) |

**Examples:**
```
# Add information to memory
manage_memory(action="store", content="Kullanici Python 3.11 tercih ediyor", category="preference")

# Search memory
manage_memory(action="search", query="Python tercihleri")

# List all records
manage_memory(action="list")

# Delete a specific record
manage_memory(action="forget", memory_id=5)
```

### 4.4 Context Management Tool

| Tool | File | Description |
|------|------|-------------|
| `update_context` | `tools/context_tool.py` | Manage the CONTEXT.md file |

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | str | `update`, `get`, `list` |
| `key` | str | Context key |
| `value` | str | Context value (for update) |

**Examples:**
```
# Update context
update_context(action="update", key="Aktif Proje", value="AETHON v0.1.0 gelistirmesi")

# Read context
update_context(action="get", key="Aktif Proje")

# List all keys
update_context(action="list")
```

Written to CONTEXT.md in `### Key\nValue` format. The agent preserves context information across sessions this way.

### 4.5 Messaging Tool

| Tool | File | Description |
|------|------|-------------|
| `send_message` | `tools/messaging.py` | Send a message to another channel |

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `channel` | str | Target channel (`telegram`, `discord`, `slack`, `webchat`) |
| `text` | str | Message text to send |
| `recipient` | str | Recipient ID (optional, default if empty) |

**Example:**
```
send_message(channel="telegram", text="Task completed!", recipient="12345678")
```

### 4.6 Scheduler Tools

| Tool | File | Description |
|------|------|-------------|
| `schedule_task` | `tools/scheduler.py` | Schedule a cron-based task |
| `list_scheduled_jobs` | `tools/scheduler.py` | List scheduled tasks |
| `remove_scheduled_job` | `tools/scheduler.py` | Remove a scheduled task |

**schedule_task Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `cron_expression` | str | Cron expression (e.g., `0 9 * * 1-5`) |
| `sop_name` | str | Name of the SOP to run |
| `job_id` | str | Task ID (optional, auto-generated) |
| `channel` | str | Result channel (optional) |

**Cron Format:** `minute hour day month dayOfWeek`

| Example | Meaning |
|---------|---------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `30 18 * * 5` | Friday at 6:30 PM |
| `0 0 1 * *` | First of every month at midnight |

### 4.7 Task Ledger Tool

| Tool | File | Description |
|------|------|-------------|
| `manage_tasks` | `tools/task_tool.py` | Manage the durable task ledger (`workspace/TASKS.json`) |

The ledger survives session resets and restarts. Tasks carry acceptance criteria and are
completed *with* verification evidence; `parent_id` / `depends_on` order multi-task work.
Registered when a task ledger is wired.

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | str | `create`, `update`, `complete`, `list` |
| `task_id` | str | Task id for `update` / `complete` (e.g. `T3`) |
| `title` | str | Task title (for `create`) |
| `acceptance_criteria` | str | Concrete definition of done |
| `status` | str | New status: `open`, `in_progress`, `done`, `dropped` |
| `evidence` | str | Verification evidence on `complete` |
| `parent_id`, `depends_on`, `priority`, `due`, `plan_origin` | str | Optional structuring fields |

### 4.8 Knowledge & Introspection Tools

| Tool | File | Description |
|------|------|-------------|
| `record_learning` | `tools/learning.py` | Persist a durable learning to `LEARNINGS.md` (read back into the system prompt when `prompt.include_learnings`). Registered unless that flag is off |
| `manage_messages` | `tools/manage_messages.py` | Turn-aware, read-only introspection of the agent's own conversation. Always available |

### 4.9 Capability Tools (config-gated)

The following tools register only when explicitly enabled, and route through the security
and approval hooks. See [CAPABILITIES.md](../CAPABILITIES.md) for full descriptions, enable
flags, and required `pip` extras.

| Tool | Enable flag | Notes |
|------|-------------|-------|
| `scraper` | `capabilities.scraper.enabled` (on) | HTML/XML scraping |
| `use_github` | `capabilities.github.enabled` (on) | GitHub GraphQL; mutations are approval-aware |
| `jsonrpc` | `capabilities.jsonrpc.enabled` (on) | JSON-RPC over HTTP/WebSocket |
| `notify` | `capabilities.notify.enabled` (on) | Native notification / bell / speech |
| `use_computer` | `capabilities.computer.enabled` (**off**) | High-risk screen/mouse/keyboard automation |
| `use_mac`, `apple_notes` | `macos.enabled` (Darwin only) | macOS native automation |
| `lsp` | `lsp.enabled` (**off**) | Language-server diagnostics / navigation |
| `manage_tools` | `runtime_tools.enabled` (**off**) | Dynamic tool creation/loading (sandbox-validated) |
| ambient tools | `ambient.enabled` (**off**) | `start_ambient_mode` / `stop_ambient_mode` / `get_ambient_status` |

---

## 5. SOP Commands

SOPs (Standard Operating Procedures) are triggered in chat with the `/` prefix.

### 5.1 Built-in SOPs

| Command | Description |
|---------|-------------|
| `/code-assist <task>` | Code writing, fixing, refactoring |
| `/pdd <task>` | Puzzle-Driven Development flow |
| `/codebase-summary <path>` | Summarize a codebase |

> `/morning-brief` is not built in — it exists only if you add it as a custom
> `.sop.md` (section 5.3) or define it as a scheduler job.

### 5.2 Running an SOP

```
User: /code-assist Bu fonksiyona hata yakalama ekle
AETHON: [Task is completed by following SOP steps]
```

### 5.3 Creating a Custom SOP

Add a file with `.sop.md` extension to the `~/.aethon/workspace/sops/` directory:

```markdown
# Custom SOP Name

## Overview
Description of what this SOP does.

## Steps
1. First step description
2. Second step description
```

If the filename is `my-sop.sop.md`, the command becomes `/my-sop`.

---

## 6. Security Layer

### 6.1 Command Blocking

Commands in the `security.blocked_commands` list are automatically blocked:

```yaml
security:
  blocked_commands:
    - "rm -rf /"
    - "sudo"
    - "mkfs"
```

### 6.2 User Verification

Channel-based allowed user list:

```yaml
security:
  allowed_senders:
    telegram: ["12345678"]
    discord: ["98765432"]
```

### 6.3 Memory Protection (MemoryGuard)

Sensitive information is automatically blocked during the `manage_memory` tool's `store` operation:

- API keys (`api_key=...`)
- Passwords (`password=...`)
- Tokens (`secret=...`, `token=...`)
- SSH keys
- Private key blocks (PEM)
- Credit card numbers
- SSN numbers

To add custom patterns:

```yaml
memory_guard:
  custom_patterns:
    - "internal_secret=\\S+"
```

### 6.4 Approval Mechanism

Dangerous tools require an interactive yes/no approval before they run. When `enabled`,
the agent pauses and prompts on the active channel (CLI/WebChat/push); the tool runs only
on an affirmative answer. If no answer arrives within `timeout_seconds`, or the channel
cannot carry an answer, the call **fails closed**.

```yaml
approval:
  enabled: false           # opt-in
  requires_approval:       # default list
    - shell
    - file_write
    - manage_tools
    - manage_specialists
  timeout_seconds: 120.0   # deny if unanswered in time
```

### 6.5 Untrusted-Content Marking

When `security.mark_untrusted_content` is on (default), content fetched from external
sources (e.g. scraped pages, HTTP responses) is wrapped/marked before it reaches the model,
so the agent treats it as data rather than trusted instructions.

```yaml
security:
  mark_untrusted_content: true
```

### 6.6 Execution Sandbox

The `shell` tool can be confined to a Docker container instead of running on the host. When
`security.sandbox: docker`, each session's shell runs in a disposable container with
network, memory, CPU, PID, and time limits.

```yaml
security:
  sandbox: docker          # "none" (default) or "docker"
  sandbox_image: python:3.12-slim
  sandbox_network: none    # no host/network access
  sandbox_read_only: true
```

See the root [SECURITY.md](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) for
the full sandbox model.

---

## 7. Error Codes

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 403 | Invalid HMAC signature (webhook) |
| 422 | Invalid request body |
| 500 | Server error |

WebSocket connection errors use standard WebSocket close codes.

---

## 8. Port Map

| Service | Port | Protocol |
|---------|------|----------|
| WebChat + Dashboard + Webhook + API | 18790 | HTTP/WS |
| Ollama | 11434 | HTTP |
| Telegram | - | HTTPS (outbound) |
| Discord | - | WSS (outbound) |
| Slack | - | WSS (outbound) |

By default all local services bind to `127.0.0.1`. Set `channels.webchat.host: 0.0.0.0`
(together with `dashboard.auth_token`) to expose AETHON on a network or inside a container;
`aethon start` refuses a non-loopback bind unless an auth token is set, or `--insecure-bind`
is passed (only behind a trusted reverse proxy).
