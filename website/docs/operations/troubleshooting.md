---
id: troubleshooting
title: Troubleshooting
sidebar_label: Troubleshooting
---

# Troubleshooting

## Provider not ready

`aethon start` runs an availability check; if it fails it prints `Provider not ready:
<msg>` and a hint. Run `aethon init` to reconfigure or `aethon doctor` to diagnose. For
API providers (OpenAI, Anthropic, …), confirm the `api_key` (or its `${ENV_VAR}`) is
actually set — remember missing env vars resolve to an empty string. If you're using an
**OpenAI-compatible endpoint**, double-check `model.host` is the right base URL, that
the server is running, and that it serves the `model_id` you configured. For **Ollama**,
make sure the daemon is running at `model.host` (default `http://localhost:11434`) and
the model is pulled.

## Port already in use (18790)

Another process holds the WebChat port. Change `channels.webchat.port`, or stop the
other process. In Docker, adjust the `18790:18790` mapping.

## Memory needs Ollama

With the default `ollama` embedding provider, vector memory requires Ollama running
with `nomic-embed-text`:

```bash
ollama pull nomic-embed-text
```

On start you'll see `Memory: nomic-embed-text not found — ollama pull nomic-embed-text`
if it's missing, or `Memory: Ollama connection error` if Ollama isn't reachable.
Alternatively switch to `embedding_provider: openai` (with `embedding_api_key`), or
disable memory.

## Docker can't reach your provider

If `model.host` points at a service on the host (e.g. a local OpenAI-compatible server
or Ollama), use `http://host.docker.internal:<port>` from inside the container and make
sure `host.docker.internal` resolves — Compose sets
`extra_hosts: host.docker.internal:host-gateway`; for plain `docker run`, add
`--add-host host.docker.internal:host-gateway`. For the official OpenAI API, just pass
`OPENAI_API_KEY` into the container.

## Messaging bot didn't start

Missing libs log a warning and missing tokens log a `ValueError` — the gateway keeps
running. Check that the channel is `enabled: true`, the token env var is set, and
(Discord) the MESSAGE CONTENT intent / (Slack) Socket Mode + event subscriptions are
configured.

## "AETHON is already running (pid N)"

A second `aethon start` exits immediately with this message. A single-instance
`flock` on `~/.aethon/aethon.pid` prevents two gateways racing for the same channels
(e.g. Telegram's long-poller, which rejects a second poller). Stop the other instance
first, or — if it crashed without releasing the lock — confirm no live process holds it.

## A channel crashed but the rest kept running

Channel adapters run under a supervisor: a crashing adapter is logged with its traceback
and **restarted with backoff** while the other channels keep serving, instead of tearing
down the whole gateway. A channel that fails permanently degrades only itself. Check the
log for the restart trail.

## Scheduled jobs / reminders after a restart

Runtime-added schedules persist to `workspace/SCHEDULE.json`, so cron jobs and one-shot
`run_at` reminders ("remind me tomorrow at 15:30") survive a restart and fire even if
the assistant was down at the scheduled moment.

## The assistant went silent on an error

On a model or runtime failure, each channel now sends a short localized error reply
pointing at `aethon doctor` instead of going quiet. Turns within a session are
serialized by a per-session lock, so a slow or failing turn can't interleave with the
next message on the same session — a second message waits for the first to finish.
