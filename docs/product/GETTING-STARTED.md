# AETHON — Getting Started Guide

> Step-by-step guide from installation to your first message.

---

## 1. Requirements

| Requirement | Minimum |
|-------------|---------|
| **Python** | 3.10+ |
| **Ollama** | Latest |
| **RAM** | 16 GB (32 GB recommended) |
| **Disk** | 50 GB (for the model) |
| **OS** | macOS (Apple Silicon recommended) |

---

## 2. Installation

### 2.1 Install Ollama

```bash
# Install Ollama (if not already installed)
brew install ollama

# Start Ollama
ollama serve
```

### 2.2 Download Models

```bash
# Main model — agent brain
ollama pull qwen3-coder-next

# Embedding model — for memory
ollama pull nomic-embed-text
```

### 2.3 Install AETHON

```bash
# Clone the project
git clone <repo-url> aethon
cd aethon

# Install dependencies
pip install -e ".[all]"
```

---

## 3. Configuration

### 3.1 Default Config

On first run, AETHON automatically creates the `~/.aethon/` directory and default files. For custom configuration:

```bash
mkdir -p ~/.aethon
```

Create `~/.aethon/config.yaml`:

```yaml
model:
  provider: ollama
  model_id: qwen3-coder-next
  host: http://localhost:11434

memory:
  enabled: true
  embedding_model: nomic-embed-text

channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 8080

multi_agent:
  enabled: true

sops:
  enabled: true

telemetry:
  enabled: true

dashboard:
  enabled: true
```

### 3.2 Workspace Files

3 essential files in the `~/.aethon/workspace/` directory:

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent's personality and behavior rules |
| `TOOLS.md` | User preferences and coding standards |
| `CONTEXT.md` | Current project/context information (automatically updated) |

---

## 4. Starting

```bash
python -m aethon start
```

Console output:

```
Starting AETHON...

  Provider: ollama
  Model: qwen3-coder-next
  WebChat: http://127.0.0.1:8080
  Memory: nomic-embed-text (active)
  Multi-Agent: active
  SOPs: 3 items
  Scheduler: active
  Telemetry: active
  Dashboard: http://127.0.0.1:8080/dashboard
  Channels: CLI, WebChat
```

---

## 5. Send Your First Message

### From CLI

After AETHON starts, type in the terminal:

```
> Merhaba, sen kimsin?
```

### From WebChat

Open in browser: `http://127.0.0.1:8080`

### From Telegram

1. Add token to `config.yaml`:
   ```yaml
   channels:
     telegram:
       enabled: true
       token: "${TELEGRAM_BOT_TOKEN}"
   ```

2. Set the token as an environment variable or save it to `~/.aethon/credentials/telegram.env`

3. Restart AETHON

---

## 6. SOP Usage

Trigger ready-made SOPs:

```
/code-assist login sayfasi implement et
/pdd yeni e-ticaret backend tasarla
/codebase-summary projeyi dokumante et
```

### Create a Custom SOP

`~/.aethon/workspace/sops/morning-brief.sop.md`:

```markdown
# Morning Brief

## Overview
Prepare a short briefing every morning.

## Steps
1. Check today's date and day
2. List priority tasks
3. Prepare a brief summary
```

Trigger: `/morning-brief`

---

## 7. Dashboard

Open in browser: `http://127.0.0.1:8080/dashboard`

What you will see:
- **Sessions** — Active sessions
- **Memory** — Long-term memory records
- **Telemetry** — Tool/Model call statistics
- **Scheduled Tasks** — Cron jobs
- **Live Metrics** — Real-time WebSocket stream

---

## 8. Next Steps

- Configure Telegram/Discord/Slack channels → see `docs/product/CONFIGURATION.md`
- Set up webhook integration → see `docs/product/API-REFERENCE.md`
- Create automated tasks with the scheduler
- Write custom SOPs
- Connect MCP servers
