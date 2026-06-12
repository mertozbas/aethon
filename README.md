# AETHON

**A self-hosted, provider-agnostic personal AI assistant — Web UI, CLI, and messaging bots, with memory, multi-agent specialists, SOPs, a scheduler, telemetry, and a live dashboard.**

[![CI](https://github.com/mertozbas/aethon/actions/workflows/ci.yml/badge.svg)](https://github.com/mertozbas/aethon/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/aethon-ai.svg)](https://pypi.org/project/aethon-ai/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm--Noncommercial--1.0.0-orange.svg)](LICENSE)
[![Built with Strands Agents SDK](https://img.shields.io/badge/built%20with-Strands%20Agents%20SDK-7d4cdb.svg)](https://github.com/strands-agents)
[![Documentation](https://img.shields.io/badge/docs-handbook-6d3fd6.svg)](https://mertozbas.github.io/aethon/)

📖 **[Read the handbook → mertozbas.github.io/aethon](https://mertozbas.github.io/aethon/)** (English · Türkçe)

> **Bring your own model provider.** AETHON is provider-agnostic: point it at the **OpenAI API** (default) or **any OpenAI-compatible endpoint** (vLLM, LM Studio, LocalAI, or any service speaking the OpenAI API), the **Anthropic API**, or a fully-local **Ollama** model — and it also supports **Bedrock, Gemini, LiteLLM, and Mistral**. You run it; you choose the backend.

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

**You bring the model provider.** AETHON defaults to **OpenAI** (`gpt-4o`): set an `api_key` for the official OpenAI API, or point `host` at **any OpenAI-compatible endpoint** — a local server like vLLM, LM Studio, or LocalAI, or any service that speaks the OpenAI API. Because everything is **local-first** (services bind to `127.0.0.1` by default and your data lives under `~/.aethon`), you stay in control of your data and your bill.

**Provider-agnostic by design:** flip one line in your config (`model.provider`) to switch between OpenAI, the Anthropic API, a fully-local Ollama model, Bedrock, Gemini, LiteLLM, or Mistral.

- **Author:** Mert Özbaş
- **Repository:** https://github.com/mertozbas/aethon
- **Version:** 0.2.0
- **License:** PolyForm Noncommercial 1.0.0 (source-available; free for noncommercial use)

---

## Features

**Model backends**
- **Bring your own provider** — defaults to **OpenAI** (`gpt-4o`) via an API key, **or** any **OpenAI-compatible base URL** (vLLM, LM Studio, LocalAI, …).
- Works with **any Strands provider**: `openai` (default), `anthropic`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral` (plus `fake`/`echo` for testing).
- Run **fully local** with Ollama — no API key, no cloud calls.
- Guided **setup wizard** (`aethon init`) and a **diagnostics** command (`aethon doctor`).

**Channels (all in one package)**
- **CLI** — terminal chat with history and Markdown rendering.
- **WebChat** — a browser chat UI served by FastAPI/uvicorn.
- **Telegram, Discord, Slack** — messaging bots (libraries ship with the core install).
- **WhatsApp** — experimental, via the optional `whatsapp` extra.

**Assistant intelligence**
- **Long-term vector memory** — SQLite-backed embeddings with cosine-similarity search.
- **Multi-agent specialists** — Coder, Researcher, Analyst, Planner, reachable from the main agent via `ask_*` delegation tools. (Swarm/Graph team & pipeline orchestration exists internally but isn't yet wired into the runtime — see [Roadmap](#roadmap).)
- **SOPs** — built-in `/code-assist`, `/pdd`, `/codebase-summary`, plus your own custom `*.sop.md` workflows.
- **Workspace persona files** — `SOUL.md`, `TOOLS.md`, `CONTEXT.md` define identity, preferences, and live state.
- **Core tools** — file read/write/edit, shell, scheduling, context updates, messaging, and MCP tools.
- **Self-improvement** — `record_learning` persists discoveries to `LEARNINGS.md`; the system prompt is **environment-aware** (OS/cwd/shell), with optional recent-logs and shell-history layers.

**Capabilities (opt-in tools)**
- **Web & APIs** — `scraper` (BeautifulSoup), `use_github` (GitHub GraphQL), `jsonrpc` (HTTP/WebSocket), `notify` (native notifications).
- **macOS native** — `use_mac` (Calendar, Reminders, Mail, Contacts, Safari, Finder, Shortcuts, Messages, Music, Keychain) and `apple_notes`, Darwin-gated with Messages/Keychain off by default.
- **Code intelligence** — `lsp` (diagnostics, go-to-def, references, hover via pyright/gopls/…) + an auto-diagnostics hook.
- **Dynamic tools** — `manage_tools` loads/creates tools at runtime in a subprocess sandbox (gated).
- **Computer control** — `use_computer` (screen/mouse/keyboard, high-risk, off by default, approval-gated).
- **Ambient / autonomous mode** — proactive idle-time work, fully opt-in.
- **Introspection** — `manage_messages` inspects the agent's own conversation, turn-aware.

**Operations & visibility**
- **Live dashboard** — overview, **Features** (capability status), live company (pixel-agents reflecting real activity), live monitor, sessions, **recordings** (session replay), memory, config, logs, agents, SOPs.
- **Session recording & replay** — record the timeline + state snapshots to a ZIP; browse and resume from the dashboard.
- **MCP server** — `aethon mcp` exposes AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over stdio.
- **Scheduler** — cron jobs that run SOPs and deliver results to a channel.
- **Webhooks** — `POST /webhook/trigger` and `POST /webhook/{channel}` with optional HMAC-SHA256 verification.
- **Telemetry** — event history with summaries surfaced in the dashboard.
- **Context safety** — oversized tool output is auto-capped so a single huge command can't overflow the model context.

**Deployment**
- **pip** install (core covers CLI + WebChat + dashboard + Telegram/Discord/Slack + memory + SOPs + scheduler).
- **Docker** image + Compose (headless, with an optional local-Ollama profile).
- **CI** on Python 3.10 / 3.11 / 3.12, with wheel/sdist build and Docker image build.

**Security & privacy**
- **Local-first**: services bind to `127.0.0.1` by default; your data lives in `~/.aethon`.
- **Workspace boundary** + **blocked-command** filtering + **approval** hooks.
- **Dashboard auth token**, **secret masking** in API config dumps, and a **memory guard** that keeps secrets out of long-term memory.

> **New in 0.2.0** — capability tools (web/GitHub/JSON-RPC/notify), macOS native tools, LSP, sandboxed dynamic tools, ambient mode, session recording/replay, and an MCP server. Full reference: [`docs/CAPABILITIES.md`](docs/CAPABILITIES.md).

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

The fastest path — install, run the wizard, chat in your browser:

```bash
pip install aethon-ai      # the PyPI package; command + import are "aethon"
aethon init                # setup wizard: pick a provider, paste a key (or go local)
aethon start               # launches the gateway + all enabled channels
# → open http://127.0.0.1:18790  (WebChat)  ·  /dashboard for the live dashboard
```

That's enough to start chatting (the terminal CLI is on by default too). **But this
quick path does not include the bundled `codex-proxy`** (the ChatGPT-Pro backend) — for
that, follow the **clone** path in the full [Installation](#installation) guide below.

> **First time on a new machine?** The next section is a complete, step-by-step
> walkthrough — prerequisites, both install paths, picking a model backend (incl.
> ChatGPT Pro via codex-proxy), and verifying it runs.

---

## Installation

A complete, first-time-on-a-new-machine walkthrough. Pick **one** install path, configure a model backend, then start.

### Prerequisites

- **Python 3.10, 3.11, or 3.12** — check with `python3 --version`. (On macOS: `brew install python`; on Debian/Ubuntu: `sudo apt install python3 python3-venv python3-pip`.)
- **git** — only needed for the clone path (Path A).
- **A model backend — pick one** (you set this up in step 2):
  - an **OpenAI API key** (the simplest), **or**
  - **ChatGPT Pro** via the bundled **`codex-proxy`** — needs **Node.js 18+** (`node --version`), **or**
  - a fully-local **Ollama** model — no key, runs offline.
- **(Optional) [Ollama](https://ollama.com)** — for the default vector-memory embeddings. `aethon init` can install it and pull the model for you; memory also works with OpenAI embeddings, or you can turn it off.

> Everything AETHON writes lives under **`~/.aethon/`** (config, sessions, memory, logs). Nothing is global except the `aethon` command.

### Path A — Clone & install (recommended)

Gets **everything**, including the bundled `codex-proxy`; updates are a `git pull`.

```bash
# 1. Clone the repository
git clone https://github.com/mertozbas/aethon.git
cd aethon

# 2. Create + activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate

# 3. Install AETHON (editable) with all optional features
pip install -e ".[all]"
#   lean alternative — core only, add extras later:  pip install -e .

# 4. Verify
aethon --version                       # → aethon, version 0.2.0
```

> **Want `aethon` available everywhere (the dev setup)?** Use **pipx** instead of a venv:
> `pipx install -e .` from the cloned folder puts an isolated `aethon` on your PATH, and
> edits to the source apply on the next run — no reinstall.

### Path B — pip install (quick; no codex-proxy)

```bash
pip install "aethon-ai[all]"           # or just: pip install aethon-ai  (core only)
aethon --version
```

The **core install ships every entry point in one package**: CLI + WebChat + dashboard + Telegram (`aiogram`) + Discord (`discord.py`) + Slack (`slack-bolt`) + memory (`aiosqlite`) + SOPs (`strands-agents-sops`) + scheduler (`apscheduler`), plus the Strands core and the default OpenAI provider. **`[all]`** adds the capability tools (web/GitHub/JSON-RPC/notify, macOS, LSP, dynamic tools, computer). **`codex-proxy` is not in the pip package** — clone (Path A) if you want it.

> **Names:** the PyPI distribution is **`aethon-ai`** (the plain `aethon` was taken), but the importable package and CLI command are both **`aethon`**. Track the latest `main` with `pip install "git+https://github.com/mertozbas/aethon.git"`.

### Configure a model backend

Run the guided wizard — it asks for your provider and writes `~/.aethon/config.yaml`:

```bash
aethon init
```

Then pick the path that matches you (full config + the codex-proxy steps are in [Model Backends](#model-backends)):

- **OpenAI API key** — paste your `sk-…` key. Simplest, works immediately.
- **ChatGPT Pro via codex-proxy** — drive AETHON from your ChatGPT plan instead of API credits. Start the bundled proxy in its own terminal:
  ```bash
  cd codex-proxy && npm install && cp .env.example .env && npm run dev   # serves :8080
  ```
  then point AETHON at `http://127.0.0.1:8080/v1`. See [ChatGPT Pro via the bundled codex-proxy](#chatgpt-pro-via-the-bundled-codex-proxy).
- **Ollama (fully local)** — no key; install the `ollama` extra and run a local model.
- **Any OpenAI-compatible endpoint** — vLLM / LM Studio / LocalAI: point `host` at its base URL.

You can re-run `aethon init` anytime, or hand-edit `~/.aethon/config.yaml`.

### First run + verify

```bash
aethon doctor      # checks provider/model + memory readiness
aethon start       # starts the gateway + every enabled channel
```

Then open:
- **WebChat** → http://127.0.0.1:18790
- **Dashboard** → http://127.0.0.1:18790/dashboard  (sessions, Features, recordings, live company, logs, …)
- **CLI** → type right in the terminal where you ran `aethon start` (`exit` to quit).

> Using codex-proxy? Keep its `npm run dev` running in a separate terminal the whole time AETHON is up — if it's down, chat requests fail with a connection error.

### Optional extras

Request an extra with `pip install "aethon-ai[ollama]"` (or `pip install -e ".[ollama]"` from a clone). Combine them, e.g. `".[ollama,lsp,computer]"`.

| Extra | Install | Adds | Purpose |
|-------|---------|------|---------|
| `anthropic` | `pip install "aethon-ai[anthropic]"` | `anthropic>=0.40.0` | The `anthropic` provider (Claude via an Anthropic API key). |
| `ollama` | `pip install "aethon-ai[ollama]"` | `ollama>=0.3.0` | Local-inference provider (run models fully offline). |
| `whatsapp` | `pip install "aethon-ai[whatsapp]"` | `neonize>=0.3.0` | WhatsApp channel (**experimental**). |
| `mcp` | `pip install "aethon-ai[mcp]"` | `mcp>=1.0.0` | MCP server support (`aethon mcp` + external MCP tools). |
| `scraper` | `pip install "aethon-ai[scraper]"` | `beautifulsoup4>=4.9.0` | `scraper` tool (HTML/XML parsing). |
| `github` | `pip install "aethon-ai[github]"` | `colorama>=0.4.0` | colored output for `use_github`. |
| `jsonrpc` | `pip install "aethon-ai[jsonrpc]"` | `websockets>=12.0` | WebSocket transport for `jsonrpc`. |
| `macos` | `pip install "aethon-ai[macos]"` | `html2text`, `mistune` | richer Markdown for `apple_notes` (use_mac needs nothing extra). |
| `lsp` | `pip install "aethon-ai[lsp]"` | `pyright>=1.1.0` | Python LSP for the `lsp` tool (other languages: install their servers). |
| `computer` | `pip install "aethon-ai[computer]"` | `pyautogui>=0.9.53` | `use_computer` (screen/mouse/keyboard). |
| `launcher-macos` | `pip install "aethon-ai[launcher-macos]"` | `rumps>=0.4.0` | macOS menu-bar launcher (`aethon-menubar`). |
| `all` | `pip install "aethon-ai[all]"` | `aethon-ai[anthropic,ollama,whatsapp,mcp,scraper,github,jsonrpc,macos,lsp,computer]` | Bundles the feature extras above. |
| `dev` | `pip install "aethon-ai[dev]"` | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.27.0` | Test/dev tooling. |

### Install with Docker

The image is **headless** (web UI + dashboard + webhook + messaging bots; the interactive CLI is disabled inside a container). Supply a provider via the seeded config or environment — by default the config uses `provider: openai` with `OPENAI_API_KEY` (or point `model.host` at an OpenAI-compatible base URL reachable from the container).

**Docker Compose (recommended):**

```bash
OPENAI_API_KEY=sk-... AETHON_DASHBOARD_TOKEN=$(openssl rand -hex 16) docker compose up --build
# open http://127.0.0.1:18790  (WebChat/dashboard ask for the token on first use)
```

> **`AETHON_DASHBOARD_TOKEN` is required.** The container binds `0.0.0.0`, so AETHON
> refuses to start when the token resolves empty (fail-closed; check `docker logs aethon`
> for the message). Only when an authenticating reverse proxy fronts the container may
> you opt out with a Compose override: `command: ["aethon", "start", "--insecure-bind"]`.

**Plain `docker run`:**

```bash
docker build -t aethon .
docker run -p 18790:18790 \
  -e OPENAI_API_KEY=sk-... \
  -e AETHON_DASHBOARD_TOKEN=change-me \
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
- **Provider:** the seeded config defaults to `provider: openai` reading `OPENAI_API_KEY` from the environment; pass it with `-e OPENAI_API_KEY=…` (or `environment:` in Compose), or set `model.host` to an OpenAI-compatible base URL.
- **Memory is disabled by default in the image** (it needs an Ollama embedding backend).
- Healthcheck probes `http://127.0.0.1:18790/health` inside the container.
- **Other providers:** switch `provider` in the config and supply the matching credentials (e.g. `ANTHROPIC_API_KEY` for `anthropic`).
- **`AETHON_DASHBOARD_TOKEN` is required** (the container binds beyond loopback; AETHON refuses to start without a token — see above).

**Reverse proxy / TLS recipe** (recommended when exposing to the internet):

```caddyfile
# Caddy — automatic HTTPS; WebSockets proxied transparently
chat.example.com {
    reverse_proxy 127.0.0.1:18790
}
```

```nginx
# nginx — terminate TLS and forward WebSocket upgrades
location / {
    proxy_pass http://127.0.0.1:18790;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

Behind TLS the chat page automatically connects via `wss:`. Keep `AETHON_DASHBOARD_TOKEN` set even behind a proxy unless the proxy itself authenticates (then `--insecure-bind` is acceptable).

### Updating & uninstalling

```bash
# Update — Path A (clone):
cd aethon && git pull && pip install -e ".[all]"     # editable picks most changes up automatically
# Update — Path B (pip):
pip install -U aethon-ai

# Uninstall (your data in ~/.aethon is left untouched):
pip uninstall aethon-ai        # or: pipx uninstall aethon-ai
# Remove your data too, if you want a clean slate:
rm -rf ~/.aethon
```

> Contributors: install the test tooling with `pip install -e ".[dev]"` and run `pytest -q` (see [Development](#development)).

---

## Model Backends

AETHON picks the provider from `model.provider` in `~/.aethon/config.yaml`. The default is **`openai`** (`gpt-4o`). The setup wizard (`aethon init`) offers a provider menu of **openai / anthropic / ollama**, defaulting to **openai**.

### OpenAI (default)

There are two ways to run the default provider — the official OpenAI API, or any **OpenAI-compatible endpoint**.

**Official OpenAI API** — supply an API key:

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}   # resolved from the environment
```

**Any OpenAI-compatible endpoint** — point `host` at a base URL instead. This works with local servers like **vLLM**, **LM Studio**, or **LocalAI**, or any service that speaks the OpenAI API. Many local servers don't need a real key (use any non-empty placeholder if one is required):

```yaml
model:
  provider: openai
  model_id: gpt-4o            # use whatever model id your endpoint serves
  host: http://localhost:8000/v1   # your OpenAI-compatible base URL
  api_key: ${OPENAI_API_KEY}       # may be a placeholder for local servers
```

> The `aethon init` wizard asks for your OpenAI API key and, optionally, an OpenAI-compatible base URL — so you usually don't hand-edit this.

### ChatGPT Pro via the bundled `codex-proxy`

This repo vendors **codex-proxy** under [`codex-proxy/`](codex-proxy/) — a reverse proxy that exposes your **ChatGPT / Codex Desktop** subscription as an **OpenAI-compatible** `/v1/chat/completions` endpoint. Point AETHON at it to drive the assistant from your **ChatGPT Pro** plan instead of spending OpenAI API credits.

> **Your secrets stay local.** codex-proxy stores account tokens under `codex-proxy/data/`, which is **gitignored** and never committed. The vendored copy ships **source + the built developer dashboard** (but no `node_modules/`, no `data/`); `npm install` restores the dependencies and the first login creates `data/`.

> ⚠️ **Use _this_ vendored copy — don't replace it with a fresh upstream clone or the prebuilt Docker image.** The vendored tree carries a small local patch that **forces stateless mode** (`AETHON_FORCE_STATELESS`, in `codex-proxy/src/routes/shared/proxy-session-helpers.ts`). AETHON resends the full conversation each turn, so the proxy's default server-side `previous_response_id` chaining only triggers a **`400` on your 2nd message** (`previous response not found` / `No tool output found for function call`). The patch disables that chaining. A stock upstream build does **not** have it and will 400 after one message. Run it from source (`npm run dev`, below) so the patch is active — not from a stale `dist/` or the `ghcr.io/...` image.

**1. Run codex-proxy** (needs Node 18+):

```bash
cd codex-proxy
npm install
cp .env.example .env          # optional: paste a CODEX_JWT_TOKEN to skip the OAuth login
npm run dev                   # serves an OpenAI-compatible API on http://127.0.0.1:8080
```

On first run, log in through the proxy (OAuth, or set `CODEX_JWT_TOKEN` in `.env`). The port is `PORT` in `.env` (default `8080`).

**2. Point AETHON at it** (`~/.aethon/config.yaml`):

```yaml
model:
  provider: openai
  model_id: gpt-5.5                 # a model your ChatGPT plan serves (e.g. gpt-5.5 / gpt-5.4)
  host: http://127.0.0.1:8080/v1    # the codex-proxy endpoint
  api_key: ${CODEX_PROXY_KEY}       # the proxy's API key (set it in codex-proxy/.env)
  max_tokens: 8192
```

Keep codex-proxy running while you use AETHON — if it's down, chat requests fail with a connection error. codex-proxy is a third-party tool vendored here for convenience; see [`codex-proxy/README.md`](codex-proxy/README.md) for its full configuration, account management, and Docker setup.

### Anthropic API

Install the extra (`pip install "aethon-ai[anthropic]"`), then:

```yaml
model:
  provider: anthropic
  model_id: claude-opus-4-8
  api_key: ${ANTHROPIC_API_KEY}   # resolved from the environment
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

Each of these backends needs its own SDK installed (none is bundled with aethon's core or an extra): `pip install boto3` (Bedrock), `google-genai` (Gemini), `litellm` (LiteLLM), or `mistralai` (Mistral).

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

The wizard walks a provider menu (**openai / anthropic / ollama**). For **openai** it asks for an API key and, optionally, an OpenAI-compatible base URL; it also configures messaging bots and, when you use Ollama embeddings for memory, offers to install Ollama and pull the embedding model. The wizard sets the provider, model, and memory and **writes the config file** for you. Use `--config / -c` to choose a path (default `~/.aethon/config.yaml`) and `--force` to overwrite an existing config without asking. After configuring, verify everything with:

```bash
aethon doctor
```

`aethon doctor` prints your provider/model, runs a provider availability check, and shows whether memory is enabled and which embedding provider it uses.

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
| `host` | str | `"127.0.0.1"` | Bind address; loopback only by default. Set `0.0.0.0` to expose — `dashboard.auth_token` is then **required** (startup refuses otherwise; `--insecure-bind` to override behind your own auth proxy). |
| `allowed_origins` | list | `[]` | Extra browser `Origin`s accepted on the WebSocket upgrades (`/ws/chat`, `/ws/dashboard`), e.g. `["https://chat.example.com"]`. Empty = same-host origins only. Mismatch closes `1008`; clients without an Origin header (curl, Python) always pass — the token is their gate. |

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
| `workspace_only` | bool | `false` | When true, confine file tools to `~/.aethon/workspace`; when false (default), allow anywhere under `$HOME` except blocked system/credential paths. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Reserved; not currently enforced. Approval gating is configured in the `approval` section. |
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
| `auth_token` | str | `""` | Shared token; empty = no auth (loopback only — a non-loopback bind **requires** it). When set, **all** routes are gated by default (deny-by-default), including `/ws/chat`, `/ws/dashboard`, every `/api/*`, and the FastAPI docs; public exceptions: `/`, `/health`, `/dashboard/static/*`, and the self-authenticating `/webhook/*`. Supplied via `?token=`, `Authorization: Bearer`, or the `aethon_dash` cookie. |

#### `webhook`

| Field | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Enable the webhook endpoint. |
| `secret` | str | `""` | Shared secret to validate incoming webhooks (HMAC-SHA256). **Fail-closed:** empty secret on a non-loopback bind disables the `/webhook/*` routes entirely (loopback: allowed, with a warning). |

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

#### Capabilities & runtime features (opt-in)

These newer blocks are all **off by default** unless noted. Powerful/host-affecting features stay disabled until you opt in, and the security & approval hooks gate the rest. (Browse live status in the dashboard's **Features** panel.)

```yaml
# Vendored utility tools (scraper/github/jsonrpc/notify default ON; computer OFF).
capabilities:
  scraper:  { enabled: true }
  github:   { enabled: true }      # use_github (reads $GITHUB_TOKEN)
  jsonrpc:  { enabled: true }
  notify:   { enabled: true, method: auto }
  computer: { enabled: false, require_approval: true }   # ⚠ screen/mouse/keyboard; needs [computer] + macOS perms

# macOS native tools (Darwin-only). Messages & Keychain are explicit opt-in.
macos:
  enabled: true
  enable_calendar: true
  enable_reminders: true
  enable_mail: true
  enable_notes: true
  enable_shortcuts: true
  enable_messages: false           # ⚠ can send iMessage/SMS as you
  enable_keychain: false           # ⚠ can read/write the Keychain
  actions_requiring_approval: ["mail.send", "messages.send", "keychain.set"]

lsp:                               # needs [lsp] (pyright) / language servers on PATH
  enabled: false
  auto_diagnostics: false          # append diagnostics after file-modifying tools

runtime_tools:                     # manage_tools (sandboxed dynamic tool loading)
  enabled: false
  allow_create: false              # create/fetch (subprocess sandbox validates first)
  allow_install: false             # add/reload (auto-install missing packages)

session_recorder:                  # timeline + snapshots → ZIP, replay in the dashboard
  enabled: false
  max_events: 10000

ambient:                           # proactive / autonomous idle-time work
  enabled: false
  auto_start: false

prompt:                            # system-prompt awareness layers
  include_environment: true
  include_learnings: true
  include_recent_logs: true
  include_shell_history: false     # privacy
  include_self_awareness: false    # embeds key source files — heavy

performance:
  max_tool_output_chars: 12000     # cap a single tool result so it can't overflow the context (0 = off)

paths:
  recordings: "~/.aethon/recordings"
```

---

## Usage

When you run `aethon start`, the console prints a status block: the provider and model, the WebChat URL (`http://127.0.0.1:18790`), the memory/multi-agent/SOP/scheduler/telemetry status, and (when enabled) the dashboard and webhook URLs and the list of active channels. Then the gateway starts.

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

To expose WebChat on your network, set `channels.webchat.host: 0.0.0.0` — `dashboard.auth_token` is then **required**: AETHON refuses to start without it (see [Security](#security)).

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

**Authentication (`dashboard.auth_token`):** empty = no auth — acceptable only on the default loopback bind (a non-loopback bind refuses to start without a token). When set, a **deny-by-default** middleware gates *everything* on the shared app — every `/api/*` route (including `/api/status`), `/dashboard`, the FastAPI docs (`/docs`, `/openapi.json`), and unknown paths (401, no route disclosure). Enumerated public exceptions: `/` (the chat page; its WebSocket is gated separately), `/health` (container/LB probes), `/dashboard/static/*` (SPA assets), and `/webhook/*` (self-authenticating HMAC, fail-closed per `webhook.secret`). Both WebSockets (`/ws/chat`, `/ws/dashboard`) check the token before accepting the upgrade and close with `1008` otherwise; the WebChat page prompts for the token on first connect and keeps it in `sessionStorage`. The token is accepted (in precedence order) via the `aethon_dash` cookie, an `Authorization: Bearer <token>` header, or a `?token=<token>` query param.

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

Webhooks mount on the WebChat app and require `webhook.enabled` (default true) with WebChat enabled. Both endpoints respond `{"status":"ok","response": <agent reply text or null>}`. If `webhook.secret` is set, requests must include `X-Aethon-Signature: <hex hmac-sha256 of the raw body>` or they're rejected with `403`. **Fail-closed:** with an empty `webhook.secret` on a non-loopback bind the routes are not registered at all (an ERROR names the missing key at startup); on loopback an empty secret still works for local development, with a warning.

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

The scheduler (APScheduler) runs cron jobs that execute an SOP and deliver the result to a channel (default channel from `scheduler.default_channel`, which is `cli`). It requires SOPs to be enabled (`sops.enabled: true`, the default). Define jobs in config:

```yaml
scheduler:
  enabled: true
  default_channel: cli
  jobs:
    weekday-standup:
      cron: "0 9 * * 1-5"        # weekdays at 9 AM
      sop_name: codebase-summary
      channel: telegram          # optional; overrides default_channel
      recipient: "123456789"     # the destination chat/channel id (see note)
```

> **Recipients:** `cli` and `webchat` need no `recipient`. For messaging channels (`telegram`, `discord`, `slack`, `whatsapp`), set `recipient` to the destination chat/channel id — otherwise delivery is skipped with a warning.

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

The SOP name is the filename with `.sop.md` removed, so `weekly-report.sop.md` is invoked as `/weekly-report`. A `## Overview` section is parsed for the SOP's description (first 200 chars), shown in listings (the dashboard SOPs panel and `/api/sops`). The agent's system prompt lists the available SOP slash-commands by name. Custom SOPs are merged with built-ins.

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

The main agent always has: `file_read, file_write, editor, shell, think, current_time`, plus `update_context` (maintains `CONTEXT.md`), `send_message` (pushes to any enabled channel), and `manage_messages` (turn-aware introspection of its own conversation). Conditionally added:

- **memory** — `manage_memory(action, content, query, category, memory_id)` when vector memory is active.
- **delegate** — `ask_coder / ask_researcher / ask_analyst / ask_planner` when the multi-agent system is on.
- **scheduler** — `schedule_task`, `list_scheduled_jobs`, `remove_scheduled_job` when the scheduler is running.
- **capabilities** — `scraper`, `use_github`, `jsonrpc`, `notify` (config-gated under `capabilities`, default on).
- **learning** — `record_learning(category, content)` when `prompt.include_learnings` (persists to `LEARNINGS.md`).
- **macOS** (Darwin) — `use_mac`, `apple_notes` when `macos.enabled`.
- **code intelligence** — `lsp` when `lsp.enabled`.
- **dynamic tools** — `manage_tools` when `runtime_tools.enabled` (sandboxed; gated by approval/security).
- **computer control** — `use_computer` when `capabilities.computer.enabled` (needs the `computer` extra).
- **ambient** — `start_ambient_mode / stop_ambient_mode / get_ambient_status` when `ambient.enabled`.
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
| `aethon init` | Set up AETHON (provider menu openai/anthropic/ollama, model, memory, messaging bots) and write the config file. | `--config, -c <path>` (default `~/.aethon/config.yaml`); `--force` (overwrite an existing config without asking). |
| `aethon doctor` | Diagnose the current configuration and provider availability (provider/model, provider check, memory). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon start` | Start AETHON (runs the setup wizard first if no config exists; launches the gateway and all enabled channels). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon mcp` | Serve AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over stdio. Informational output goes to stderr. | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon --version` | Print `aethon, version 0.2.0` and exit. | — |

Also installed with the `launcher-macos` extra: **`aethon-menubar`** — a macOS menu-bar launcher (Start/Stop server, open WebChat, settings).

---

## Security

AETHON is **local-first** and ships safe defaults:

- **Loopback binding:** WebChat (and the dashboard/webhooks mounted on it) bind to `127.0.0.1` by default. To expose beyond localhost, set `channels.webchat.host: 0.0.0.0` **and** a `dashboard.auth_token` — without the token AETHON **refuses to start** (fail closed; `--insecure-bind` overrides only behind your own authenticating proxy).
- **Shared auth token (deny by default):** when `dashboard.auth_token` is set, **all** routes require the token — `/ws/chat`, `/ws/dashboard`, every `/api/*`, `/dashboard`, the FastAPI docs, and unknown paths. Public exceptions: `/`, `/health`, `/dashboard/static/*`, and the HMAC-authenticated `/webhook/*`. Token via `aethon_dash` cookie, `Authorization: Bearer`, or `?token=`.
- **File-access sandbox:** by default, file tools may read/write anywhere under your home directory **except** a blocklist of system and credential paths (`/etc`, `/usr`, `/bin`, `~/.ssh`, `~/.gnupg`, `~/.aethon/credentials`, …). Set `security.workspace_only: true` to confine file tools strictly to `~/.aethon/workspace`.
- **Blocked commands:** the security hook refuses shell commands containing any `security.blocked_commands` entry (default `rm -rf /`, `sudo`, `mkfs`, plus a built-in danger list).
- **Approval gating:** an optional interrupt-based hook can require approval for the actions in `approval.requires_approval` (default `shell`, `file_write`) — it is **off by default** (`approval.enabled: false`). *(The `security.require_approval` field is reserved and not currently enforced.)*
- **Sender allowlists:** `security.allowed_senders` can restrict who may message each channel.
- **Secret masking:** the dashboard `GET /api/config` dump masks sensitive keys (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) to `***`.
- **Memory guard:** the memory guard hook blocks secrets from being written to long-term memory.
- **Webhook verification:** set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming webhooks. Webhooks **fail closed**: an empty secret on a non-loopback bind disables the `/webhook/*` routes (Docker: set `AETHON_WEBHOOK_SECRET`).
- **Credential isolation:** keep tokens out of the config file by referencing `${ENV_VAR}`s and storing secrets under `~/.aethon/credentials/`.

---

## Troubleshooting

**Provider not ready.** `aethon start` runs an availability check; if it fails it prints `Provider not ready: <msg>` and a hint. Run `aethon init` to reconfigure or `aethon doctor` to diagnose. For API providers (OpenAI, Anthropic, …), confirm the `api_key` (or its `${ENV_VAR}`) is actually set — remember missing env vars resolve to an empty string. If you're using an **OpenAI-compatible endpoint**, double-check `model.host` is the right base URL, that the server is running, and that it serves the `model_id` you configured. For **Ollama**, make sure the daemon is running at `model.host` (default `http://localhost:11434`) and the model is pulled.

**Port already in use (18790).** Another process holds the WebChat port. Change `channels.webchat.port`, or stop the other process. In Docker, adjust the `18790:18790` mapping.

**Memory needs Ollama.** With the default `ollama` embedding provider, vector memory requires Ollama running with `nomic-embed-text`:

```bash
ollama pull nomic-embed-text
```

On start you'll see `Memory: nomic-embed-text not found — ollama pull nomic-embed-text` if it's missing, or `Memory: Ollama connection error` if Ollama isn't reachable. Alternatively switch to `embedding_provider: openai` (with `embedding_api_key`), or disable memory.

**Docker can't reach your provider.** If `model.host` points at a service on the host (e.g. a local OpenAI-compatible server or Ollama), use `http://host.docker.internal:<port>` from inside the container and make sure `host.docker.internal` resolves — Compose sets `extra_hosts: host.docker.internal:host-gateway`; for plain `docker run`, add `--add-host host.docker.internal:host-gateway`. For the official OpenAI API, just pass `OPENAI_API_KEY` into the container.

**Messaging bot didn't start.** Missing libs log a warning and missing tokens log a `ValueError` — the gateway keeps running. Check that the channel is `enabled: true`, the token env var is set, and (Discord) the MESSAGE CONTENT intent / (Slack) Socket Mode + event subscriptions are configured.

---

## FAQ

**Do I need an API key?**
For the default OpenAI provider, yes — supply `OPENAI_API_KEY` (or point `model.host` at an OpenAI-compatible endpoint, where local servers often accept a placeholder key). To run with **no key at all**, use the fully-local **Ollama** provider. API providers like Anthropic also need their own key.

**Where does AETHON store my data?**
Under `~/.aethon` — config (`config.yaml`), workspace (`workspace/`), sessions (`sessions/`), logs (`logs/`), vector memory (`memory.sqlite`), and credentials (`credentials/`).

**Is AETHON open source?**
It's **source-available** under PolyForm Noncommercial 1.0.0 — free for noncommercial use, but **not** OSI-approved open source (commercial use isn't permitted). See [License](#license).

**Can I run it fully offline / locally?**
Yes. Install the `ollama` extra, set `provider: ollama`, and use Ollama embeddings for memory. No cloud calls are required in that configuration.

**How do I expose the Web UI on my network?**
Set `channels.webchat.host: 0.0.0.0` and **also** set `dashboard.auth_token` (required — AETHON refuses to start exposed without it). Then reach the dashboard with `?token=YOUR_TOKEN` to set the auth cookie.

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

**v1 (0.1.0) shipped:** the full provider-agnostic assistant — CLI + WebChat + dashboard, Telegram/Discord/Slack channels, SQLite vector memory, multi-agent specialists with `ask_*` delegation, built-in and custom SOPs, scheduler, webhooks, telemetry, bring-your-own model provider (OpenAI default, plus Anthropic / Ollama / Bedrock / Gemini / LiteLLM / Mistral), and Docker + CI infrastructure.

**0.2.0 — capability expansion (this release):**
- **Capability tools** — `scraper`, `use_github`, `jsonrpc`, `notify`, `manage_messages`.
- **macOS native** — `use_mac` + `apple_notes` (Darwin-gated; Messages/Keychain off by default).
- **Code intelligence** — `lsp` tool + auto-diagnostics hook.
- **Dynamic tool loading** — `manage_tools` with a subprocess sandbox + 3-layer gating.
- **Computer control** — `use_computer` (opt-in, approval-gated).
- **Ambient / autonomous mode** — proactive idle-time work (opt-in).
- **Session recording & replay** — recorder hook + replay API + dashboard tab.
- **MCP server** — `aethon mcp` exposes the toolset to MCP clients.
- **System-prompt awareness** — environment / learnings / recent-logs / shell-history layers + `record_learning`.
- **Dashboard** — Features panel + identity-correct Live Company + context-overflow protection.

**Still deferred:**
- Response **streaming**.
- **Team / pipeline orchestration** (Swarm/Graph) wired into the runtime and exposed as a command/tool.
- **Per-specialist multi-model** configuration.
- Real-time **voice** (STT/TTS).

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
- **[OpenAI](https://platform.openai.com/)** — the default model provider (`gpt-4o`); also reachable via any OpenAI-compatible endpoint.
- **[Ollama](https://ollama.com/)** — fully-local model serving and the default memory-embedding backend.

---

<p align="center"><sub>Built by Mert Özbaş · <a href="https://github.com/mertozbas/aethon">github.com/mertozbas/aethon</a></sub></p>
