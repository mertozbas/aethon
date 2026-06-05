# AETHON — API Reference

> All HTTP endpoints, WebSocket protocols, webhook integrations, and agent tools.

---

## 1. WebChat Endpoints

AETHON listens on `http://127.0.0.1:18790` by default.

### 1.1 WebChat UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ui` | GET | WebChat interface (HTML) |

**Example:**
```
GET http://127.0.0.1:18790/ui
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
    "provider": "ollama",
    "model_id": "claude-opus-4-8",
    "host": "http://localhost:11434",
    "temperature": 1.0,
    "max_tokens": 16384
  },
  "memory": { "enabled": true, "..." : "..." },
  "channels": { "..." : "..." }
}
```

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

### 2.8 Live Telemetry Stream

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws/telemetry` | WebSocket | Real-time metric stream |

**Connection:**
```javascript
const ws = new WebSocket("ws://127.0.0.1:18790/ws/telemetry");
ws.onmessage = (e) => {
  const metric = JSON.parse(e.data);
  console.log(metric.type, metric.name, metric.duration);
};
```

**Metric Format:**
```json
{
  "type": "tool",
  "name": "shell",
  "duration": 0.32,
  "status": "success",
  "timestamp": "2026-03-12T14:30:15"
}
```

The server pushes new metrics every 2 seconds.

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

### 4.1 Strands Built-in Tools

| Tool | Import | Description |
|------|--------|-------------|
| `file_read` | `strands_tools` | Read a file |
| `file_write` | `strands_tools` | Write a file |
| `editor` | `strands_tools` | Edit a file (diff-based) |
| `shell` | `strands_tools` | Run in the command line |
| `python_repl` | `strands_tools` | Run Python code |
| `http_request` | `strands_tools` | Send an HTTP request |
| `calculator` | `strands_tools` | Mathematical calculation |
| `think` | `strands_tools` | Internal thought (planning) |
| `current_time` | `strands_tools` | Current date/time |

### 4.2 Specialist Delegation Tools

| Tool | File | Description |
|------|------|-------------|
| `ask_coder` | `tools/delegate.py` | Delegate a coding task to the coder specialist |
| `ask_researcher` | `tools/delegate.py` | Delegate a research task to the researcher |
| `ask_analyst` | `tools/delegate.py` | Delegate an analysis task to the analyst |
| `ask_planner` | `tools/delegate.py` | Delegate a planning task to the planner |

**Parameter:**
- `task` (str): Description of the task for the specialist

**How It Works:** The main agent delegates the task to the appropriate specialist. The specialist completes the task using its own tools and returns the result.

### 4.3 Memory Management Tool

| Tool | File | Description |
|------|------|-------------|
| `manage_memory` | `tools/memory_tool.py` | Manage long-term memory |

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | str | `store`, `search`, `list`, `forget`, `count` |
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

# Get record count
manage_memory(action="count")
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

---

## 5. SOP Commands

SOPs (Standard Operating Procedures) are triggered in chat with the `/` prefix.

### 5.1 Built-in SOPs

| Command | Description |
|---------|-------------|
| `/code-assist <task>` | Code writing, fixing, refactoring |
| `/pdd <task>` | Puzzle-Driven Development flow |
| `/morning-brief` | Morning briefing report |

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
    - "sudo "
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

User approval requirement for dangerous tools:

```yaml
approval:
  enabled: true
  requires_approval:
    - shell
    - file_write
```

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

All local services are bound to `127.0.0.1`. `0.0.0.0` is not used.
