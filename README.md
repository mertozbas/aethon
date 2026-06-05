# AETHON

**A self-hosted, provider-agnostic personal AI assistant — Web UI, CLI, and messaging bots, with memory, multi-agent specialists, SOPs, a scheduler, telemetry, and a live dashboard.**

[![CI](https://github.com/mertozbas/aethon/actions/workflows/ci.yml/badge.svg)](https://github.com/mertozbas/aethon/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/aethon-ai.svg)](https://pypi.org/project/aethon-ai/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm--Noncommercial--1.0.0-orange.svg)](LICENSE)
[![Built with Strands Agents SDK](https://img.shields.io/badge/built%20with-Strands%20Agents%20SDK-7d4cdb.svg)](https://github.com/strands-agents)

> By default, AETHON runs **Claude (Opus 4.8)** on **your Claude Max subscription quota** through the local **Meridian** proxy — **no per-token API bills**. It still works with **any Strands provider** (Anthropic API, OpenAI, Ollama, Bedrock, Gemini, LiteLLM, Mistral) if you prefer.

---

## What is AETHON?

AETHON is a **personal AI assistant you run yourself**. It is a single Python package that ships every entry point you need to talk to one persistent, memory-backed assistant:

- a **terminal CLI** for interactive chat,
- a **Web UI (WebChat)** in your browser,
- **messaging bots** for Telegram, Discord, Slack, and (experimentally) WhatsApp,
- a **live dashboard** to watch sessions, memory, telemetry, agents, and SOPs in real time,
- **webhooks** so other systems can trigger the assistant,
- and a **cron scheduler** so the assistant can run jobs on a timetable.

Under the hood, AETHON is built on the **Strands Agents SDK**. A main orchestrator agent can delegate to **specialist sub-agents** (Coder, Researcher, Analyst, Planner), keep **long-term vector memory** of what matters to you, follow **SOPs** (Standard Operating Procedures — reusable, slash-invoked workflows), and call **tools** (files, shell, scheduling, messaging, MCP servers).

The headline value is the **default model backend**. Instead of paying per token to an API, AETHON defaults to **Claude Opus 4.8 served through Meridian** — a small local proxy that bridges the Claude Code SDK to Anthropic using your **Claude Max subscription**. You install Meridian once, log in with your Claude account, and AETHON auto-starts the proxy for you. Because everything is **local-first** (services bind to `127.0.0.1` by default and your data lives under `~/.aethon`), you stay in control of your data and your bill.

**Provider-agnostic by design:** flip one line in your config (`model.provider`) to switch to the Anthropic API, OpenAI, a fully-local Ollama model, Bedrock, Gemini, LiteLLM, or Mistral.

- **Author:** Mert Özbaş
- **Repository:** https://github.com/mertozbas/aethon
- **Version:** 0.1.0
- **License:** PolyForm Noncommercial 1.0.0 (source-available; free for noncommercial use)

---

## Features

**Model backends**
- Defaults to **Claude Opus 4.8** via the **Meridian** proxy on your **Claude Max** quota — no API key, no per-token cost.
- **Auto-starts Meridian** in the background on `aethon start` (no extra terminal to babysit).
- Works with **any Strands provider**: `meridian`, `anthropic`, `openai`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral` (plus `fake`/`echo` for testing).
- Guided **setup wizard** (`aethon init`) and a **diagnostics** command (`aethon doctor`).

**Channels (all in one package)**
- **CLI** — terminal chat with history and Markdown rendering.
- **WebChat** — a browser chat UI served by FastAPI/uvicorn.
- **Telegram, Discord, Slack** — messaging bots (libraries ship with the core install).
- **WhatsApp** — experimental, via the optional `whatsapp` extra.

**Assistant intelligence**
- **Long-term vector memory** — SQLite-backed embeddings with cosine-similarity search.
- **Multi-agent specialists** — Coder, Researcher, Analyst, Planner, with `ask_*` delegation tools and team/pipeline modes.
- **SOPs** — built-in `/code-assist`, `/pdd`, `/codebase-summary`, plus your own custom `*.sop.md` workflows.
- **Workspace persona files** — `SOUL.md`, `TOOLS.md`, `CONTEXT.md` define identity, preferences, and live state.
- **Tools** — file read/write/edit, shell, scheduling, context updates, messaging, and MCP tools.

**Operations & visibility**
- **Live dashboard** — overview, live company (pixel-agents), live monitor, sessions, memory, config, logs, agents, SOPs.
- **Scheduler** — cron jobs that run SOPs and deliver results to a channel.
- **Webhooks** — `POST /webhook/trigger` and `POST /webhook/{channel}` with optional HMAC-SHA256 verification.
- **Telemetry** — event history with summaries surfaced in the dashboard.
- **MCP** — optional Model Context Protocol server integration.

**Deployment**
- **pip** install (core covers CLI + WebChat + dashboard + Telegram/Discord/Slack + memory + SOPs + scheduler).
- **Docker** image + Compose (headless, with an optional local-Ollama profile).
- **CI** on Python 3.10 / 3.11 / 3.12, with wheel/sdist build and Docker image build.

**Security & privacy**
- **Local-first**: services bind to `127.0.0.1` by default; your data lives in `~/.aethon`.
- **Workspace boundary** + **blocked-command** filtering + **approval** hooks.
- **Dashboard auth token**, **secret masking** in API config dumps, and a **memory guard** that keeps secrets out of long-term memory.

---

## Table of Contents

- [What is AETHON?](#what-is-aethon)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Model Backends](#model-backends)
- [Configuration](#configuration)
- [Usage](#usage)
- [Core Concepts](#core-concepts)
- [CLI Reference](#cli-reference)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Architecture](#architecture)
- [Development](#development)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Quick Start

The fastest path runs AETHON on your **Claude Max** quota via Meridian — no API key required.

```bash
# 1) Install Meridian once (Node/npm), and log in with your Claude account.
npm install -g @rynfar/meridian
claude login          # one-time; uses your Claude subscription

# 2) Install AETHON. (The PyPI distribution is named "aethon-ai";
#    the command and import stay "aethon".)
pip install aethon-ai

# 3) Start. The first run launches the setup wizard if no config exists,
#    and auto-starts the Meridian proxy in the background for you.
aethon start

# 4) Open the Web UI.
#    http://127.0.0.1:18790
```

That's it. You can also chat right in your terminal (the CLI channel is on by default), and visit the dashboard at **http://127.0.0.1:18790/dashboard**.

> If you'd rather not run on Claude Max, see [Model Backends](#model-backends) for the Anthropic API, OpenAI, and fully-local Ollama paths.

---

## Installation

### Requirements

- **Python 3.10, 3.11, or 3.12** (`requires-python = ">=3.10"`).
- **For the default Meridian/Claude-Max backend:** Node.js + npm (to install `@rynfar/meridian`) and a Claude subscription (`claude login`).
- **For vector memory with the default settings:** a running **Ollama** with the `nomic-embed-text` model pulled (see [Memory](#memory-vector--embeddings)). Memory is enabled by default but only needs Ollama when you keep the default `ollama` embedding provider.
- **Build backend:** `hatchling` (only relevant if you build from source).

### Install with pip

```bash
pip install aethon-ai
```

> **Note on names:** the PyPI distribution is **`aethon-ai`** (the plain `aethon` name was already taken), but the importable package and the CLI command are both **`aethon`** — so you run `aethon start` and `import aethon` as usual. To track the latest `main` instead, install from GitHub: `pip install "git+https://github.com/mertozbas/aethon.git"`.

The **core install ships every entry point in one package**: CLI + WebChat + dashboard + Telegram (`aiogram`) + Discord (`discord.py`) + Slack (`slack-bolt`) + memory (`aiosqlite`) + SOPs (`strands-agents-sops`) + scheduler (`apscheduler`), plus the Strands core and the default `strands-meridian` provider.

#### Optional extras

Request an extra with `pip install "aethon-ai[ollama]"`. From a local clone, the equivalent is `pip install ".[ollama]"` (see [Development](#development)).

| Extra | Install | Adds | Purpose |
|-------|---------|------|---------|
| `ollama` | `pip install "aethon-ai[ollama]"` | `ollama>=0.3.0` | Local-inference provider (run models fully offline). |
| `whatsapp` | `pip install "aethon-ai[whatsapp]"` | `neonize>=0.3.0` | WhatsApp channel (**experimental**). |
| `mcp` | `pip install "aethon-ai[mcp]"` | `mcp>=1.0.0` | MCP (Model Context Protocol) server support. |
| `all` | `pip install "aethon-ai[all]"` | `aethon-ai[ollama,whatsapp,mcp]` | Bundles the three feature extras above. |
| `dev` | `pip install "aethon-ai[dev]"` | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.27.0` | Test/dev tooling. |

### Install with Docker

The image is **headless** (web UI + dashboard + webhook + messaging bots; the interactive CLI is disabled inside a container). It defaults to talking to a **Meridian proxy running on your host** at `http://host.docker.internal:3456`, so start `meridian` on the host first.

**Docker Compose (recommended):**

```bash
docker compose up --build
# open http://127.0.0.1:18790
```

**Plain `docker run`:**

```bash
docker build -t aethon .
docker run -p 18790:18790 \
  --add-host host.docker.internal:host-gateway \
  aethon
```

**Bundle the Ollama client at build time** (for the local-inference path):

```bash
docker compose build --build-arg EXTRAS=ollama
# or: docker build --build-arg EXTRAS=ollama -t aethon .
```

**Fully-local inference with the Compose `local` profile** (runs an `ollama/ollama` service named `aethon-ollama` on port `11434`):

```bash
docker compose --profile local up --build
# Then, in the data volume's config.yaml, set:
#   model.provider: ollama
#   model.host: http://ollama:11434
# (and build the image with EXTRAS=ollama so it has the Ollama client)
```

**Docker facts worth knowing:**
- Base image: multi-stage `python:3.12-slim` (builder + runtime), runs as non-root user `aethon` (uid 10001) at `WORKDIR /home/aethon`.
- State/config live in the named volume **`aethon-data`** mounted at `/home/aethon/.aethon`. The seeded `docker/config.docker.yaml` is copied to `/home/aethon/.aethon/config.yaml` **only when the volume is empty** — a mounted config/volume takes precedence.
- WebChat binds **`0.0.0.0:18790`** inside the container so the `18790:18790` port mapping reaches it.
- **Meridian auto-start is OFF in Docker** (the slim image has no Node runtime) — run Meridian on the host.
- **Memory is disabled by default in the image** (it needs an Ollama embedding backend).
- Healthcheck probes `http://127.0.0.1:18790/health` inside the container.
- **API-key alternative:** uncomment `ANTHROPIC_API_KEY` in `docker-compose.yml` and switch `provider: anthropic` in the config. Set `AETHON_DASHBOARD_TOKEN` to enable dashboard auth when exposing beyond localhost.

### Install from source

```bash
git clone https://github.com/mertozbas/aethon.git
cd aethon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"     # editable install with dev tooling
aethon --version
```

---

## Model Backends

AETHON picks the provider from `model.provider` in `~/.aethon/config.yaml`. The default is **`meridian`** (Claude on your Claude Max quota). The setup wizard (`aethon init`) offers a provider menu of **meridian / anthropic / openai / ollama**, defaulting to **meridian**.

### The default path — Claude on Claude Max via Meridian (step by step)

1. **Install Meridian** (one time, on the host):
   ```bash
   npm install -g @rynfar/meridian
   ```
2. **Log in** with your Claude account (one time):
   ```bash
   claude login
   ```
3. **Start AETHON.** Because `model.provider` is `meridian` and `meridian.auto_start` is `true`, AETHON checks whether the proxy is reachable at `http://127.0.0.1:3456` and, if not, **spawns it detached in the background** for you:
   ```bash
   aethon start
   ```
   On start you'll see lines like `Meridian: starting in the background…` then `Meridian: started in the background (pid …; logs: …)`.

**What Meridian does:** it bridges the Claude Code SDK to the Anthropic API using your **Claude Max subscription**, so you don't pay per token and you don't need an API key. The proxy listens on **`http://127.0.0.1:3456`**. AETHON launches it from a neutral working directory (`~/.aethon`) so another project's `CLAUDE.md` doesn't leak into the assistant's context, logs to `~/.aethon/logs/meridian.log`, and writes its pid to `~/.aethon/meridian.pid`.

**Default model config (no key needed):**

```yaml
model:
  provider: meridian
  model_id: claude-opus-4-8     # 1M context included with Claude Max
  # host is ignored by Meridian; the proxy is used at 127.0.0.1:3456

meridian:
  auto_start: true              # set false to manage Meridian yourself
```

> Prefer to run Meridian by hand? Set `meridian.auto_start: false` and start `meridian` yourself before `aethon start`.

### Anthropic API

```yaml
model:
  provider: anthropic
  model_id: claude-opus-4-8
  api_key: ${ANTHROPIC_API_KEY}   # resolved from the environment
```

### OpenAI

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

### Ollama (fully local)

Install the extra (`pip install "aethon-ai[ollama]"`), then:

```yaml
model:
  provider: ollama
  model_id: llama3.1
  host: http://localhost:11434
```

### Other providers (bedrock / gemini / litellm / mistral)

These are also supported by the model factory. Set `provider` accordingly and supply the parameters each backend needs — for example `region` (default `us-west-2`) for **Bedrock**-style backends, and `api_key` for **Gemini / Mistral**. The `litellm` provider only uses `model_id` (configure credentials via LiteLLM's own environment variables, not `model.api_key`). `model.extra` is forwarded only for the `ollama` provider (merged into its sampling `options`); bedrock/gemini/litellm/mistral ignore `extra`.

```yaml
model:
  provider: bedrock
  model_id: anthropic.claude-3-5-sonnet
  region: us-west-2
```

> **Note:** `temperature` is intentionally omitted for `claude-opus-4-8` requests.

### Let the wizard do it: `aethon init`

```bash
aethon init
```

The wizard sets the provider, model, and memory and **writes the config file** for you. Use `--config / -c` to choose a path (default `~/.aethon/config.yaml`) and `--force` to overwrite an existing config without asking. After configuring, verify everything with:

```bash
aethon doctor
```

`aethon doctor` prints your provider/model, runs a provider availability check, reports Meridian status, and shows whether memory is enabled and which embedding provider it uses.

---

## Configuration

- **File location:** `~/.aethon/config.yaml` (override with `--config / -c` on any command).
- **Format:** YAML, validated with Pydantic. A **missing or empty file produces a fully-defaulted config** — every section falls back to its defaults.
- **Writing:** the wizard and tooling write YAML with `sort_keys=False` and `allow_unicode=True`, creating parent directories as needed.

### `${ENV_VAR}` resolution

A string value is treated as an environment-variable reference **only if it starts with `${` and ends with `}`** (whole-string only — no partial or interpolated substitution). The inner name is looked up via `os.environ`. **A missing env var resolves to an empty string `""`**, not an error. Resolution recurses into dicts and lists; ints, bools, floats, and `None` pass through unchanged.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}   # actual secret supplied via the environment
```

> Docs suggest keeping secrets in files like `~/.aethon/credentials/telegram.env` and exporting them into the environment.

### Complete reference

#### `model`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `provider` | str | `"meridian"` | Model provider backend (meridian, anthropic, openai, ollama, …). |
| `host` | str | `"http://localhost:11434"` | Ollama host URL; Meridian ignores it and uses `127.0.0.1:3456`. |
| `model_id` | str | `"claude-opus-4-8"` | Model identifier; 1M context included with Claude Max. |
| `api_key` | str | `""` | API key for the provider. |
| `temperature` | float | `1.0` | Sampling temperature. |
| `top_p` | float | `0.95` | Nucleus sampling probability mass. |
| `top_k` | int | `40` | Top-k sampling cutoff. |
| `max_tokens` | int | `8192` | Max tokens to generate per response. |
| `region` | str | `"us-west-2"` | Provider region (e.g. for Bedrock-style backends). |
| `extra` | dict | `{}` | Arbitrary extra provider params. |

#### `meridian`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `auto_start` | bool | `true` | Auto-start Meridian in the background on `aethon start` if not running; set false to manage it yourself. |

#### `channels`

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

#### `security`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `workspace_only` | bool | `true` | Restrict file/tool operations to the workspace directory. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Action types that require approval. |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Shell command substrings that are blocked. |
| `allowed_senders` | dict[str, list[str]] | `{}` | Per-channel allowlist of sender identifiers. |

#### `session`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `storage_dir` | str | `"~/.aethon/sessions"` | Directory where session state is stored. |
| `conversation_manager` | str | `"summarizing"` | Conversation manager strategy. |
| `summary_ratio` | float | `0.3` | Fraction of history to summarize when compacting. |
| `preserve_recent_messages` | int | `10` | Number of recent messages kept verbatim. |

#### `memory`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable vector memory. |
| `embedding_provider` | str | `"ollama"` | Embedding provider (ollama, openai). |
| `embedding_model` | str | `"nomic-embed-text"` | Embedding model name. |
| `embedding_api_key` | str | `""` | API key for the embedding provider. |
| `db_path` | str | `"~/.aethon/memory.sqlite"` | SQLite path for the vector store. |

#### `multi_agent`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the multi-agent system. |
| `max_handoffs` | int | `10` | Max agent-to-agent handoffs. |
| `max_iterations` | int | `10` | Max iterations per run. |
| `execution_timeout` | float | `300.0` | Overall execution timeout (seconds). |
| `node_timeout` | float | `120.0` | Per-node timeout (seconds). |

#### `sops`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable SOP execution. |
| `builtin_sops_enabled` | bool | `true` | Enable built-in SOPs. |

#### `approval`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable the interrupt-based approval hook. |
| `requires_approval` | list[str] | `["shell", "file_write"]` | Action types requiring approval via this hook. |

#### `telemetry`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the telemetry hook. |
| `max_history` | int | `10000` | Max telemetry events retained. |

#### `memory_guard`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the memory guard hook. |
| `custom_patterns` | list[str] | `[]` | Additional patterns the guard should catch. |

#### `scheduler`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the scheduler. |
| `default_channel` | str | `"cli"` | Default channel for scheduled outputs. |
| `jobs` | dict | `{}` | Scheduled job definitions. |

#### `dashboard`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the web dashboard. |
| `pixel_agents` | bool | `true` | Enable the pixel-agents visualization. |
| `auth_token` | str | `""` | Optional shared token; empty = no auth. Gates `/dashboard` and protected `/api/*` + `/ws/dashboard` via `?token=`, `Authorization: Bearer`, or the `aethon_dash` cookie. |

#### `webhook`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the webhook endpoint. |
| `secret` | str | `""` | Shared secret to validate incoming webhooks (HMAC-SHA256). |

#### `mcp`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `false` | Enable MCP server integration. |
| `servers` | list[dict] | `[]` | List of MCP server definitions. |

#### `performance`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `model_warmup` | bool | `false` | Send a real model request on boot to reduce first-message latency (off by default; spends quota). |
| `session_cache_size` | int | `10` | Number of sessions cached in memory. |
| `embedding_cache_size` | int | `100` | Number of embeddings cached. |

#### `paths`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `workspace` | str | `"~/.aethon/workspace"` | Workspace root directory. |
| `sessions` | str | `"~/.aethon/sessions"` | Sessions directory. |
| `memory_db` | str | `"~/.aethon/memory.sqlite"` | Vector memory SQLite path. |
| `logs` | str | `"~/.aethon/logs"` | Logs directory. |
| `credentials` | str | `"~/.aethon/credentials"` | Credentials directory. |

> **Notes:** `~` in path-valued fields is stored literally; it is expanded only for the config-file path itself in `load()`/`write()`. Some values overlap intentionally (e.g. `memory.db_path` and `paths.memory_db` both default to `~/.aethon/memory.sqlite`; `session.storage_dir` and `paths.sessions` both `~/.aethon/sessions`).

---

## Usage

When you run `aethon start`, the console prints a status block: the provider and model, the WebChat URL (`http://127.0.0.1:18790`), the Meridian/memory/multi-agent/SOP/scheduler/telemetry status, and (when enabled) the dashboard and webhook URLs and the list of active channels. Then the gateway starts.

### Interactive CLI

The CLI channel is enabled by default. After `aethon start`, type at the `you > ` prompt. Responses render as Markdown. Input history is saved to `~/.aethon/cli_history`. Exit with `exit`, `quit`, `q`, or Ctrl-C / EOF.

```
you > what's on my plate today?
you > /code-assist refactor the auth module
you > exit
```

### Web UI (WebChat)

Open **http://127.0.0.1:18790** in your browser. It's a minimal dark chat UI (header, message list, input + Send) that connects over a WebSocket (`/ws/chat`) and renders bot replies as Markdown. You send plain text; you get one reply per message.

Useful endpoints on the same app/port:
- `GET /api/status` → `{"status": "running", "version": "0.1.0"}` (not gated).
- `GET /health` → `{"status": "ok"}` (deliberately ungated, for container/load-balancer probes).

To expose WebChat on your network, set `channels.webchat.host: 0.0.0.0` — and also set `dashboard.auth_token` (see [Security](#security)).

### Dashboard

Open **http://127.0.0.1:18790/dashboard**. The dashboard is a single-page app (self-hosted fonts/CSS, works offline) with these panels:

| Route | Panel |
|---|---|
| `#/overview` | Overview |
| `#/company` | Live Company (pixel-agents) |
| `#/monitor` | Live Monitor |
| `#/sessions` | Sessions |
| `#/memory` | Memory |
| `#/config` | Config (secrets masked to `***`) |
| `#/logs` | Logs |
| `#/agents` | Agents |
| `#/sops` | SOPs |

The dashboard mounts on the WebChat app and is only available when **WebChat is enabled** and `dashboard.enabled` is true.

**Authentication (`dashboard.auth_token`):** empty = no auth (fine for the default localhost bind). When set, an HTTP middleware gates `/dashboard` and the protected `/api/*` prefixes (`/api/sessions`, `/api/memory`, `/api/config`, `/api/scheduler`, `/api/telemetry`, `/api/sops`, `/api/agents`) and `/ws/dashboard`. Note `/api/status` and `/health` stay open. The token is accepted (in precedence order) via the `aethon_dash` cookie, an `Authorization: Bearer <token>` header, or a `?token=<token>` query param.

The usual flow when a token is set:

```
# Open once with the token; the server sets the aethon_dash cookie for you.
http://127.0.0.1:18790/dashboard?token=YOUR_TOKEN

# API calls (Bearer header):
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:18790/api/config

# WebSocket (cookie or ?token=):
ws://127.0.0.1:18790/ws/dashboard?token=YOUR_TOKEN
```

**Liveness/health:** `GET /health` always returns `{"status": "ok"}`, even when a dashboard token is set.

### Messaging bots

Enable a channel under `channels.<name>` and supply its token(s) (typically via `${ENV_VAR}`). The gateway starts only enabled channels and won't crash on missing tokens — it logs the error and keeps going.

**Telegram** — create a bot via **BotFather** to get the token.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}
```

**Discord** — create a bot in the **Discord Developer Portal** and grant it the **MESSAGE CONTENT** intent. The bot responds to DMs or messages that @mention it.

```yaml
channels:
  discord:
    enabled: true
    token: ${DISCORD_BOT_TOKEN}
```

**Slack** — create a **Slack App**, enable **Socket Mode**, and subscribe to events `message.channels`, `message.im`, `app_mention`. You need both a Bot Token and an App-Level Token.

```yaml
channels:
  slack:
    enabled: true
    bot_token: ${SLACK_BOT_TOKEN}    # xoxb-…
    app_token: ${SLACK_APP_TOKEN}    # xapp-…
```

**WhatsApp (experimental)** — install the extra (`pip install "aethon-ai[whatsapp]"`), enable the channel, and on first start scan the **QR code** with your WhatsApp app to link the session.

```yaml
channels:
  whatsapp:
    enabled: true
```

### Webhooks

Webhooks mount on the WebChat app and require `webhook.enabled` (default true) with WebChat enabled. Both endpoints respond `{"status":"ok","response": <agent reply text or null>}`. If `webhook.secret` is set, requests must include `X-Aethon-Signature: <hex hmac-sha256 of the raw body>` or they're rejected with `403`.

**Run a SOP and get the reply back** (`POST /webhook/trigger`):

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"sop_name": "code-assist", "text": "summarize the repo"}'
```

**Push the reply out to another channel too:**

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"text": "deploy finished", "channel": "telegram", "recipient": "123456"}'
```

**Channel-specific inbound** (`POST /webhook/{channel}`) — the response is returned in the HTTP body:

```bash
curl -X POST http://127.0.0.1:18790/webhook/github \
  -H 'Content-Type: application/json' \
  -d '{"text": "PR #42 merged"}'
```

### Scheduler (cron jobs)

The scheduler (APScheduler) runs cron jobs that execute an SOP and deliver the result to a channel (default channel from `scheduler.default_channel`, which is `cli`). Define jobs in config:

```yaml
scheduler:
  enabled: true
  default_channel: cli
  jobs:
    weekday-standup:
      cron: "0 9 * * 1-5"        # weekdays at 9 AM
      sop_name: codebase-summary
      channel: telegram          # optional; overrides default_channel
```

The assistant can also manage jobs at runtime with the `schedule_task`, `list_scheduled_jobs`, and `remove_scheduled_job` tools (see [Agent tools](#agent-tools)).

---

## Core Concepts

### Workspace files (SOUL / TOOLS / CONTEXT)

On `aethon start`, AETHON ensures the workspace at `~/.aethon/workspace` exists and seeds three Markdown files (each written only if it doesn't already exist — your edits are preserved):

- **`SOUL.md`** — the assistant's persona/system identity. Sections: **Identity** (be pragmatic and direct; own mistakes; say when you don't know), **Communication** (speaks English and Turkish, replies in the user's language; short focused answers; Markdown formatting), **Decision Making** (do simple tasks directly; propose a plan for complex tasks; pick the simplest approach).
- **`TOOLS.md`** — your preferences and capabilities. Sections: **Code Standards** (Python 3.10+, type hints, f-strings, asyncio + OOP, no needless comments, test against real data), **Expert Delegation** (`ask_coder`, `ask_researcher`, `ask_analyst`, `ask_planner`), **Memory** (save with `manage_memory`; categories preferences/projects/decisions/learnings; never store secrets), **Context** (keep `CONTEXT.md` current with `update_context`).
- **`CONTEXT.md`** — live working state, seeded with empty placeholders for **Active Project**, **Recent Decisions**, and **Notes**.

It also creates `<workspace>/sops`, the sessions directory, the logs directory, and (if memory is enabled) the memory DB's parent directory.

### Memory (vector + embeddings)

Long-term memory is a **SQLite vector store** with **provider embeddings** and **cosine-similarity** search (a brute-force full scan; no ANN index). Storage lives at `~/.aethon/memory.sqlite` by default.

- **Ollama embeddings (default):** uses `config.model.host` (default `http://localhost:11434`) and model `nomic-embed-text`. Requires Ollama running with that model pulled.
- **OpenAI embeddings:** set `memory.embedding_provider: openai` and `memory.embedding_api_key`.

The assistant manages memory with the `manage_memory` tool — actions `store`, `search`, `list`, and `forget`, with categories like `preferences`, `projects`, `decisions`, `learnings`. The **memory guard** hook keeps secrets out of long-term memory.

### Multi-agent specialists + delegation (`ask_*`)

A main orchestrator agent can delegate complex work to four specialists (all share the runtime's model):

| id | name | focus | tools |
|----|------|-------|-------|
| `coder` | Coder | writing code, testing, debugging, refactoring (TDD) | `file_read, file_write, editor, shell, python_repl, think` |
| `researcher` | Researcher | web research, reading docs, gathering info (cites sources) | `http_request, file_read, think, current_time` |
| `analyst` | Analyst | data analysis, calculations, charts, reports | `python_repl, calculator, file_read, file_write, think` |
| `planner` | Planner | breaking complex tasks into concrete steps, prioritization | `file_read, file_write, think` |

Delegation tools: `ask_coder(task)`, `ask_researcher(query)`, `ask_analyst(data_task)`, `ask_planner(planning_task)`. The orchestrator is instructed to handle simple tasks itself and delegate complex ones.

Beyond `ask_*`, two team modes exist internally: a **collaborative** mode (a Strands `Swarm` with handoffs, governed by `multi_agent.max_handoffs / max_iterations / execution_timeout / node_timeout`) and a **pipeline** mode (a deterministic `GraphBuilder` sequence; default pipeline `["planner", "researcher", "coder"]`).

### SOPs (Standard Operating Procedures)

SOPs are reusable workflows invoked with a slash command. **Built-ins:**

```
/code-assist        /pdd        /codebase-summary
```

(from the `strands-agents-sops` package; toggle with `sops.builtin_sops_enabled`, and the whole subsystem with `sops.enabled`).

**Invoking:** a message that starts with `/` is treated as an SOP command; the first token after `/` is the SOP name and the rest is your input. It only matches loaded SOPs.

**Authoring a custom SOP:** create a Markdown file at:

```
~/.aethon/workspace/sops/<name>.sop.md
```

The SOP name is the filename with `.sop.md` removed, so `weekly-report.sop.md` is invoked as `/weekly-report`. A `## Overview` section is parsed for the SOP's description (first 200 chars) shown in listings and in the system prompt. Custom SOPs are merged with built-ins.

```markdown
## Overview
Generate a concise weekly status report from recent commits and notes.

## Steps
1. Summarize recent activity.
2. Highlight blockers and decisions.
3. Output a Markdown report.
```

You can also create/edit/delete custom SOPs from the dashboard's SOPs panel (built-ins can't be deleted).

### Agent tools

The main agent always has: `file_read, file_write, editor, shell, think, current_time`. Conditionally added:

- **memory** — `manage_memory(action, content, query, category, memory_id)` when vector memory is active.
- **delegate** — `ask_coder / ask_researcher / ask_analyst / ask_planner` when the multi-agent system is on.
- **update_context** — `update_context(action, key, value)` to maintain `CONTEXT.md` (actions `update`, `get`, `list`).
- **send_message** — `send_message(channel, text, recipient)` to push messages out via `telegram`, `discord`, `slack`, or `webchat`.
- **scheduler** — `schedule_task(cron_expression, sop_name, job_id, channel)`, `list_scheduled_jobs()`, `remove_scheduled_job(job_id)`.
- **MCP tools** — appended when MCP is enabled.

### Telemetry

The telemetry hook records events (up to `telemetry.max_history`, default 10000) and surfaces summaries and recent metrics in the dashboard (`/api/telemetry`, the Live Monitor, and Agents/history views).

---

## CLI Reference

```bash
aethon [--version] <command> [options]
```

| Command | Description | Options |
|---|---|---|
| `aethon init` | Set up AETHON (provider, model, memory) and write the config file. | `--config, -c <path>` (default `~/.aethon/config.yaml`); `--force` (overwrite an existing config without asking). |
| `aethon doctor` | Diagnose the current configuration and provider availability (provider/model, provider check, Meridian status, memory). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon start` | Start AETHON (runs the setup wizard first if no config exists; auto-starts Meridian when applicable; launches the gateway and all enabled channels). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon --version` | Print `aethon, version 0.1.0` and exit. | — |

---

## Security

AETHON is **local-first** and ships safe defaults:

- **Loopback binding:** WebChat (and the dashboard/webhooks mounted on it) bind to `127.0.0.1` by default. To expose beyond localhost, set `channels.webchat.host: 0.0.0.0` **and** a `dashboard.auth_token`.
- **Dashboard auth token:** when `dashboard.auth_token` is set, `/dashboard`, the protected `/api/*` prefixes, and `/ws/dashboard` require the token (via `aethon_dash` cookie, `Authorization: Bearer`, or `?token=`). `/api/status` and `/health` stay open for probes.
- **Workspace boundary:** `security.workspace_only` (default true) restricts file/tool operations to the workspace.
- **Approval & blocked commands:** `security.require_approval` (default `shell`, `file_write`, `send_message`) and `security.blocked_commands` (default `rm -rf /`, `sudo`, `mkfs`) gate dangerous actions; an additional interrupt-based approval hook is available via the `approval` section.
- **Sender allowlists:** `security.allowed_senders` can restrict who may message each channel.
- **Secret masking:** the dashboard `GET /api/config` dump masks sensitive keys (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) to `***`.
- **Memory guard:** the memory guard hook blocks secrets from being written to long-term memory.
- **Webhook verification:** set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming webhooks.
- **Credential isolation:** keep tokens out of the config file by referencing `${ENV_VAR}`s and storing secrets under `~/.aethon/credentials/`.

---

## Troubleshooting

**Meridian not reachable / `Provider not ready`.** Ensure Meridian is installed and you're logged in:

```bash
npm install -g @rynfar/meridian
claude login
```

AETHON auto-starts Meridian on `aethon start` (when `provider: meridian` and `meridian.auto_start: true`). If auto-start times out, check the log at `~/.aethon/logs/meridian.log` and re-run `claude login` if needed. The proxy listens on `http://127.0.0.1:3456`. Run `aethon doctor` to see Meridian status.

**Provider not ready (other backends).** `aethon start` runs an availability check; if it fails it prints `Provider not ready: <msg>` and a hint. Run `aethon init` to reconfigure or `aethon doctor` to diagnose. For API providers, confirm the `api_key` (or its `${ENV_VAR}`) is actually set — remember missing env vars resolve to an empty string.

**Port already in use (18790).** Another process holds the WebChat port. Change `channels.webchat.port`, or stop the other process. In Docker, adjust the `18790:18790` mapping.

**Memory needs Ollama.** With the default `ollama` embedding provider, vector memory requires Ollama running with `nomic-embed-text`:

```bash
ollama pull nomic-embed-text
```

On start you'll see `Memory: nomic-embed-text not found — ollama pull nomic-embed-text` if it's missing, or `Memory: Ollama connection error` if Ollama isn't reachable. Alternatively switch to `embedding_provider: openai` (with `embedding_api_key`), or disable memory.

**Docker can't reach host Meridian.** The container talks to host Meridian at `http://host.docker.internal:3456`. Make sure `meridian` is running on the host, and that `host.docker.internal` resolves — Compose sets `extra_hosts: host.docker.internal:host-gateway`; for plain `docker run`, add `--add-host host.docker.internal:host-gateway`.

**Messaging bot didn't start.** Missing libs log a warning and missing tokens log a `ValueError` — the gateway keeps running. Check that the channel is `enabled: true`, the token env var is set, and (Discord) the MESSAGE CONTENT intent / (Slack) Socket Mode + event subscriptions are configured.

---

## FAQ

**Do I need an API key?**
No — not for the default path. With `provider: meridian` and a Claude subscription (`claude login`), AETHON runs Claude Opus 4.8 on your **Claude Max** quota with no API key and no per-token bill. API keys are only needed if you choose the Anthropic API, OpenAI, etc.

**Where does AETHON store my data?**
Under `~/.aethon` — config (`config.yaml`), workspace (`workspace/`), sessions (`sessions/`), logs (`logs/`), vector memory (`memory.sqlite`), and credentials (`credentials/`).

**Is AETHON open source?**
It's **source-available** under PolyForm Noncommercial 1.0.0 — free for noncommercial use, but **not** OSI-approved open source (commercial use isn't permitted). See [License](#license).

**Can I run it fully offline / locally?**
Yes. Install the `ollama` extra, set `provider: ollama`, and use Ollama embeddings for memory. No cloud calls are required in that configuration.

**How do I expose the Web UI on my network?**
Set `channels.webchat.host: 0.0.0.0` and **also** set `dashboard.auth_token`. Then reach the dashboard with `?token=YOUR_TOKEN` to set the auth cookie.

**Which channels need extra installs?**
Only **WhatsApp** (the `whatsapp` extra). CLI, WebChat, Telegram, Discord, and Slack all ship in the core install.

**How do I add my own workflow?**
Drop a `*.sop.md` file in `~/.aethon/workspace/sops/` (with an `## Overview` section) and invoke it as `/<name>`. See [SOPs](#sops-standard-operating-procedures).

**Does the assistant remember things between sessions?**
Yes, when memory is enabled. It stores embeddings in SQLite and retrieves them by similarity. The memory guard prevents secrets from being saved.

---

## Architecture

AETHON is a Strands-Agents application with a single FastAPI/uvicorn server (owned by the WebChat adapter) that also hosts the dashboard and webhook routers, so everything shares one host/port. A **gateway** instantiates the enabled **channel adapters** and routes inbound messages to the **agent runtime**, which composes a system prompt from the workspace files, holds the **vector memory**, wires up the **specialist factory** and **SOP runner**, and exposes the **tools**. Cross-cutting **hooks** provide telemetry, approval, and the memory guard. Optional **MCP** servers extend the toolset.

For deeper reference, see the documentation under [`docs/`](https://github.com/mertozbas/aethon/tree/main/docs):

- [`docs/product/ARCHITECTURE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/ARCHITECTURE.md) — system architecture.
- [`docs/product/PRODUCT.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/PRODUCT.md) — product overview.
- [`docs/product/GETTING-STARTED.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/GETTING-STARTED.md) — getting started.
- [`docs/product/CONFIGURATION.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/CONFIGURATION.md) — configuration guide.
- [`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md) — HTTP/WebSocket API reference.
- [`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md) — security model & threat analysis.
- [`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md) — roadmap.

---

## Development

```bash
git clone https://github.com/mertozbas/aethon.git
cd aethon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**Run tests** (the `e2e` marker spawns a subprocess and binds a socket; the `ollama` marker needs a running Ollama):

```bash
pytest                       # full suite
pytest -q                    # quiet
pytest -m "not e2e"          # skip end-to-end boot tests
```

**Lint** (the error-level gate CI enforces):

```bash
ruff check --select E9,F63,F7,F82 aethon
```

**CI** (`.github/workflows/ci.yml`, name `CI`, on push/PR to `main`) runs three jobs:
- `test` — matrix on Python 3.10 / 3.11 / 3.12; `pip install -e ".[dev]"`; ruff error-level lint; `pytest -q`.
- `build` — `python -m build` + `twine check dist/*` on 3.12.
- `docker` — builds image `aethon:ci` (no push).

Contributions follow the same noncommercial terms; see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Roadmap

**v1 (0.1.0) ships:** the full provider-agnostic assistant — CLI + WebChat + dashboard, Telegram/Discord/Slack channels, SQLite vector memory, multi-agent specialists with delegation and teams, built-in and custom SOPs, scheduler, webhooks, telemetry, the Meridian/Claude-Max default backend with background auto-start, and Docker + CI infrastructure.

**Deferred to v2:**
- Response **streaming**.
- **Per-specialist multi-model** configuration.
- **Tool Builder** and **Agent Builder** agents.
- **Phase 7** AI Capabilities Expansion.

See [`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md) for details.

---

## License

AETHON is licensed under the **PolyForm Noncommercial License 1.0.0**.

- **Free for any noncommercial use** — personal, research, education, and hobby use are all permitted.
- **Commercial use is not permitted** under this license.
- **Source-available, not OSI open source** — you can read and modify the source within the noncommercial terms, but it is not an OSI-approved open-source license.

See the full text in [LICENSE](LICENSE).

---

## Acknowledgements

- **[Strands Agents SDK](https://github.com/strands-agents)** — the agent framework AETHON is built on.
- **[Meridian](https://github.com/rynfar/meridian)** (`@rynfar/meridian`) — the local proxy that bridges the Claude Code SDK to Anthropic using your Claude Max subscription.
- **[strands-meridian](https://github.com/mertozbas/strands-meridian)** — the Strands provider that wraps Meridian (AETHON's default backend).
- **[Anthropic Claude](https://www.anthropic.com/claude)** — the default model (Claude Opus 4.8).

---

<p align="center"><sub>Built by Mert Özbaş · <a href="https://github.com/mertozbas/aethon">github.com/mertozbas/aethon</a></sub></p>
