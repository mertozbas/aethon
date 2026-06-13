---
id: docker
title: Docker
sidebar_label: Docker
---

# Install with Docker

The image is **headless** (web UI + dashboard + webhook + messaging bots; the
interactive CLI is disabled inside a container). Supply a provider via the seeded
config or environment — by default the config uses `provider: openai` with
`OPENAI_API_KEY` (or point `model.host` at an OpenAI-compatible base URL reachable
from the container).

:::warning A dashboard token is REQUIRED in the container
The container always binds WebChat to `0.0.0.0` (so the port mapping reaches it), and
AETHON **refuses to start on a non-loopback bind without an auth token**. Always pass
`AETHON_DASHBOARD_TOKEN` (any sufficiently long secret — e.g. `$(openssl rand -hex 16)`).
Behind your own authenticating reverse proxy you may instead override the command with
`aethon start --insecure-bind`.
:::

## Docker Compose (recommended)

```bash
AETHON_DASHBOARD_TOKEN=$(openssl rand -hex 16) \
OPENAI_API_KEY=sk-... \
docker compose up --build
# then open http://127.0.0.1:18790/dashboard?token=YOUR_TOKEN
# (plain WebChat at /ws/chat also needs the token + an allowed Origin)
```

## Plain `docker run`

```bash
docker build -t aethon .
docker run -p 18790:18790 \
  -e AETHON_DASHBOARD_TOKEN=$(openssl rand -hex 16) \
  -e OPENAI_API_KEY=sk-... \
  aethon
```

## Bundle the Ollama client at build time

For the local-inference path:

```bash
docker compose build --build-arg EXTRAS=ollama
# or: docker build --build-arg EXTRAS=ollama -t aethon .
```

## Fully-local inference with the Compose `local` profile

Runs an `ollama/ollama` service named `aethon-ollama` on port `11434`:

```bash
docker compose --profile local up --build
# Then, in the data volume's config.yaml, set:
#   model.provider: ollama
#   model.host: http://ollama:11434
# (and build the image with EXTRAS=ollama so it has the Ollama client)
```

## Docker facts worth knowing

- **Base image:** multi-stage `python:3.12-slim` (builder + runtime), runs as non-root user `aethon` (uid 10001) at `WORKDIR /home/aethon`.
- **State/config** live in the named volume **`aethon-data`** mounted at `/home/aethon/.aethon`. The seeded `docker/config.docker.yaml` is copied to `/home/aethon/.aethon/config.yaml` **only when the volume is empty** — a mounted config/volume takes precedence.
- **Binding:** WebChat binds **`0.0.0.0:18790`** inside the container so the `18790:18790` port mapping reaches it.
- **Provider:** the seeded config defaults to `provider: openai` reading `OPENAI_API_KEY` from the environment; pass it with `-e OPENAI_API_KEY=…` (or `environment:` in Compose), or set `model.host` to an OpenAI-compatible base URL.
- **Memory is disabled by default in the image** (it needs an Ollama embedding backend).
- **Healthcheck** probes `http://127.0.0.1:18790/health` inside the container.
- **Other providers:** switch `provider` in the config and supply the matching credentials (e.g. `ANTHROPIC_API_KEY` for `anthropic`).
- **`AETHON_DASHBOARD_TOKEN` is REQUIRED for the image** — the container always binds `0.0.0.0`, and AETHON refuses to start on a non-loopback bind without it. Behind your own authenticating reverse proxy you can override the command with `aethon start --insecure-bind` instead of setting a token.
- **Webhooks fail closed in the container:** with `AETHON_WEBHOOK_SECRET` unset the `/webhook/*` routes are simply **not registered** (the rest keeps running). Set it to enable them — callers then sign the request body with HMAC-SHA256 in the `X-Aethon-Signature` header.

:::warning Docker can't reach your provider?
If `model.host` points at a service on the host (e.g. a local OpenAI-compatible server
or Ollama), use `http://host.docker.internal:<port>` from inside the container and make
sure `host.docker.internal` resolves — Compose sets
`extra_hosts: host.docker.internal:host-gateway`; for plain `docker run`, add
`--add-host host.docker.internal:host-gateway`. For the official OpenAI API, just pass
`OPENAI_API_KEY` into the container.
:::
