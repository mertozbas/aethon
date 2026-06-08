---
id: model-backends
title: Model Backends
sidebar_label: Model Backends
---

# Model Backends

AETHON picks the provider from `model.provider` in `~/.aethon/config.yaml`. The
default is **`openai`** (`gpt-4o`). The setup wizard (`aethon init`) offers a
provider menu of **openai / anthropic / ollama**, defaulting to **openai**.

## OpenAI (default)

There are two ways to run the default provider — the official OpenAI API, or any
**OpenAI-compatible endpoint**.

**Official OpenAI API** — supply an API key:

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}   # resolved from the environment
```

**Any OpenAI-compatible endpoint** — point `host` at a base URL instead. This works
with local servers like **vLLM**, **LM Studio**, or **LocalAI**, or any service that
speaks the OpenAI API. Many local servers don't need a real key (use any non-empty
placeholder if one is required):

```yaml
model:
  provider: openai
  model_id: gpt-4o            # use whatever model id your endpoint serves
  host: http://localhost:8000/v1   # your OpenAI-compatible base URL
  api_key: ${OPENAI_API_KEY}       # may be a placeholder for local servers
```

:::tip
The `aethon init` wizard asks for your OpenAI API key and, optionally, an
OpenAI-compatible base URL — so you usually don't hand-edit this.
:::

## ChatGPT Pro via the bundled `codex-proxy`

The repo vendors **codex-proxy** under `codex-proxy/` — a reverse proxy that exposes
your **ChatGPT / Codex Desktop** subscription as an **OpenAI-compatible**
`/v1/chat/completions` endpoint. Point AETHON at it to drive the assistant from your
**ChatGPT Pro** plan instead of spending OpenAI API credits.

:::info Your secrets stay local
codex-proxy stores account tokens under `codex-proxy/data/`, which is **gitignored**
and never committed. The vendored copy ships **source only** (no `node_modules/`, no
`data/`); `npm install` restores the dependencies and the first login creates `data/`.
:::

**1. Run codex-proxy** (needs Node 18+):

```bash
cd codex-proxy
npm install
cp .env.example .env          # optional: paste a CODEX_JWT_TOKEN to skip the OAuth login
npm run dev                   # serves an OpenAI-compatible API on http://127.0.0.1:8080
```

On first run, log in through the proxy (OAuth, or set `CODEX_JWT_TOKEN` in `.env`).
The port is `PORT` in `.env` (default `8080`).

**2. Point AETHON at it** (`~/.aethon/config.yaml`):

```yaml
model:
  provider: openai
  model_id: gpt-5.5                 # a model your ChatGPT plan serves (e.g. gpt-5.5 / gpt-5.4)
  host: http://127.0.0.1:8080/v1    # the codex-proxy endpoint
  api_key: ${CODEX_PROXY_KEY}       # the proxy's API key (set it in codex-proxy/.env)
  max_tokens: 8192
```

Keep codex-proxy running while you use AETHON — if it's down, chat requests fail with
a connection error. codex-proxy is a third-party tool vendored here for convenience;
see its own `README.md` for full configuration, account management, and Docker setup.

## Anthropic API

Install the extra (`pip install "aethon-ai[anthropic]"`), then:

```yaml
model:
  provider: anthropic
  model_id: claude-opus-4-8
  api_key: ${ANTHROPIC_API_KEY}   # resolved from the environment
```

:::note
`temperature` is intentionally omitted for `claude-opus-4-8` requests.
:::

## Ollama (fully local)

Install the extra (`pip install "aethon-ai[ollama]"`), then:

```yaml
model:
  provider: ollama
  model_id: llama3.1
  host: http://localhost:11434
```

No API key, no cloud calls — everything runs on your machine.

## Other providers (bedrock / gemini / litellm / mistral)

These are also supported by the model factory. Set `provider` accordingly and supply
the parameters each backend needs — for example `region` (default `us-west-2`) for
**Bedrock**-style backends, and `api_key` for **Gemini / Mistral**. The `litellm`
provider only uses `model_id` (configure credentials via LiteLLM's own environment
variables, not `model.api_key`). `model.extra` is forwarded only for the `ollama`
provider (merged into its sampling `options`); bedrock/gemini/litellm/mistral ignore
`extra`.

Each of these backends needs its own SDK installed (none is bundled with aethon's
core or an extra): `pip install boto3` (Bedrock), `google-genai` (Gemini), `litellm`
(LiteLLM), or `mistralai` (Mistral).

```yaml
model:
  provider: bedrock
  model_id: anthropic.claude-3-5-sonnet
  region: us-west-2
```

## Let the wizard do it: `aethon init`

```bash
aethon init
```

The wizard walks a provider menu (**openai / anthropic / ollama**). For **openai** it
asks for an API key and, optionally, an OpenAI-compatible base URL; it also configures
messaging bots and, when you use Ollama embeddings for memory, offers to install
Ollama and pull the embedding model. The wizard sets the provider, model, and memory
and **writes the config file** for you. Use `--config / -c` to choose a path (default
`~/.aethon/config.yaml`) and `--force` to overwrite an existing config without asking.
After configuring, verify everything with:

```bash
aethon doctor
```

`aethon doctor` prints your provider/model, runs a provider availability check, and
shows whether memory is enabled and which embedding provider it uses.
