# AETHON — Getting Started Guide

> Step-by-step guide from installation to your first message.

---

## 1. Requirements

| Requirement | Minimum |
|-------------|---------|
| **Python** | 3.10+ |
| **Model provider** | An [OpenAI](https://platform.openai.com) API key (default) — *or* any OpenAI-compatible endpoint (vLLM / LM Studio / LocalAI / …) — *or* [Ollama](https://ollama.com) for fully-local inference |
| **RAM** | 8 GB (16 GB+ if running a local model via Ollama) |
| **OS** | macOS, Linux, or Windows |

AETHON is **provider-agnostic** — you bring your own model provider. The default is **OpenAI**,
either through the official API (set an `api_key`) or by pointing `host` at any OpenAI-compatible
base URL. If you prefer to run everything locally with no API key, use **Ollama** instead.

---

## 2. Installation

### 2.1 Install AETHON

```bash
pip install aethon-ai
```

This installs the `aethon` command (and the `aethon` import). To work from source:

```bash
git clone https://github.com/mertozbas/aethon aethon
cd aethon
pip install -e ".[all]"
```

### 2.2 Choose a model provider

AETHON defaults to **OpenAI**. Provide one of the following:

**Default — OpenAI API:**

```bash
export OPENAI_API_KEY=sk-...   # your OpenAI API key
```

**OpenAI-compatible endpoint (local or hosted):** point `host` at any base URL that speaks the
OpenAI API — e.g. a local vLLM / LM Studio / LocalAI server, or any compatible service. No
official OpenAI key is needed in that case; the endpoint's own key (if any) goes in `api_key`.

**Alternative — fully local via Ollama (no API key):**

```bash
brew install ollama
ollama serve
ollama pull qwen3-coder-next     # a local LLM
ollama pull nomic-embed-text     # embedding model (used for vector memory)
```

> The fastest way to wire all of this up is the setup wizard — see **2.3**.

### 2.3 Run the setup wizard (recommended)

```bash
aethon init
```

`aethon init` walks you through a provider menu (**openai / anthropic / ollama**). For **openai**
it asks for an API key and, optionally, an OpenAI-compatible base URL. It also configures your
messaging bots (Telegram / Discord / Slack) and, when you choose Ollama embeddings, offers to
install Ollama and pull the embedding model for you.

---

## 3. Configuration

### 3.1 Default Config

On first run, AETHON automatically creates the `~/.aethon/` directory and default files. The
quickest way to generate a config is `aethon init` (see 2.3). For custom configuration:

```bash
mkdir -p ~/.aethon
```

Create `~/.aethon/config.yaml`:

```yaml
model:
  provider: openai                   # default — official OpenAI API
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}
  # host: https://your-openai-compatible-endpoint/v1   # OR any OpenAI-compatible base URL
  #                                                     # (vLLM / LM Studio / LocalAI / …)
  # provider: ollama                 # fully-local alternative (no API key):
  # model_id: qwen3-coder-next
  # host: http://localhost:11434

memory:
  enabled: true
  embedding_model: nomic-embed-text

channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 18790

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

  Provider: openai
  Model: gpt-4o
  WebChat: http://127.0.0.1:18790
  Memory: nomic-embed-text (active)
  Multi-Agent: active
  SOPs: 3 loaded
  Scheduler: active
  Telemetry: active
  Dashboard: http://127.0.0.1:18790/dashboard
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

Open in browser: `http://127.0.0.1:18790`

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

Open in browser: `http://127.0.0.1:18790/dashboard`

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
