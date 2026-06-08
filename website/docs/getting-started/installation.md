---
id: installation
title: Installation
sidebar_label: Installation
---

# Installation

A complete, first-time-on-a-new-machine walkthrough. Pick **one** install path,
configure a model backend, then start.

## Quick start

The fastest path — install, run the wizard, chat in your browser:

```bash
pip install aethon-ai      # the PyPI package; command + import are "aethon"
aethon init                # setup wizard: pick a provider, paste a key (or go local)
aethon start               # launches the gateway + all enabled channels
# → open http://127.0.0.1:18790  (WebChat)  ·  /dashboard for the live dashboard
```

That's enough to start chatting (the terminal CLI is on by default too). **But this
quick path does not include the bundled `codex-proxy`** (the ChatGPT-Pro backend) —
for that, follow the **clone** path (Path A) below.

## Prerequisites

- **Python 3.10, 3.11, or 3.12** — check with `python3 --version`. (On macOS: `brew install python`; on Debian/Ubuntu: `sudo apt install python3 python3-venv python3-pip`.)
- **git** — only needed for the clone path (Path A).
- **A model backend — pick one** (you set this up in step 2):
  - an **OpenAI API key** (the simplest), **or**
  - **ChatGPT Pro** via the bundled **`codex-proxy`** — needs **Node.js 18+** (`node --version`), **or**
  - a fully-local **Ollama** model — no key, runs offline.
- **(Optional) [Ollama](https://ollama.com)** — for the default vector-memory embeddings. `aethon init` can install it and pull the model for you; memory also works with OpenAI embeddings, or you can turn it off.

:::note
Everything AETHON writes lives under **`~/.aethon/`** (config, sessions, memory,
logs). Nothing is global except the `aethon` command.
:::

## Path A — Clone & install (recommended)

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

:::tip Want `aethon` available everywhere (the dev setup)?
Use **pipx** instead of a venv: `pipx install -e .` from the cloned folder puts an
isolated `aethon` on your PATH, and edits to the source apply on the next run — no
reinstall.
:::

## Path B — pip install (quick; no codex-proxy)

```bash
pip install "aethon-ai[all]"           # or just: pip install aethon-ai  (core only)
aethon --version
```

The **core install ships every entry point in one package**: CLI + WebChat +
dashboard + Telegram (`aiogram`) + Discord (`discord.py`) + Slack (`slack-bolt`) +
memory (`aiosqlite`) + SOPs (`strands-agents-sops`) + scheduler (`apscheduler`),
plus the Strands core and the default OpenAI provider. **`[all]`** adds the
capability tools (web/GitHub/JSON-RPC/notify, macOS, LSP, dynamic tools, computer).
**`codex-proxy` is not in the pip package** — clone (Path A) if you want it.

:::info Package names
The PyPI distribution is **`aethon-ai`** (the plain `aethon` was taken), but the
importable package and CLI command are both **`aethon`**. Track the latest `main`
with `pip install "git+https://github.com/mertozbas/aethon.git"`.
:::

## Configure a model backend

Run the guided wizard — it asks for your provider and writes `~/.aethon/config.yaml`:

```bash
aethon init
```

Then pick the path that matches you (full config + the codex-proxy steps are in
**[Model Backends](./model-backends.md)**):

- **OpenAI API key** — paste your `sk-…` key. Simplest, works immediately.
- **ChatGPT Pro via codex-proxy** — drive AETHON from your ChatGPT plan instead of API credits. Start the bundled proxy in its own terminal:
  ```bash
  cd codex-proxy && npm install && cp .env.example .env && npm run dev   # serves :8080
  ```
  then point AETHON at `http://127.0.0.1:8080/v1`.
- **Ollama (fully local)** — no key; install the `ollama` extra and run a local model.
- **Any OpenAI-compatible endpoint** — vLLM / LM Studio / LocalAI: point `host` at its base URL.

You can re-run `aethon init` anytime, or hand-edit `~/.aethon/config.yaml`.

## First run + verify

```bash
aethon doctor      # checks provider/model + memory readiness
aethon start       # starts the gateway + every enabled channel
```

Then open:

- **WebChat** → http://127.0.0.1:18790
- **Dashboard** → http://127.0.0.1:18790/dashboard  (sessions, Features, recordings, live company, logs, …)
- **CLI** → type right in the terminal where you ran `aethon start` (`exit` to quit).

:::warning Using codex-proxy?
Keep its `npm run dev` running in a separate terminal the whole time AETHON is up —
if it's down, chat requests fail with a connection error.
:::

## Optional extras

Request an extra with `pip install "aethon-ai[ollama]"` (or `pip install -e ".[ollama]"`
from a clone). Combine them, e.g. `".[ollama,lsp,computer]"`.

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
| `all` | `pip install "aethon-ai[all]"` | the feature extras above | Bundles the feature extras. |
| `dev` | `pip install "aethon-ai[dev]"` | `pytest`, `pytest-asyncio`, `httpx` | Test/dev tooling. |

## Updating & uninstalling

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

:::note Running in a container?
See the **[Docker guide](./docker.md)** for the headless image, Compose, and the
local-Ollama profile.
:::
