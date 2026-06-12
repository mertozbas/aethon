---
id: api
title: HTTP & WebSocket API
sidebar_label: HTTP API
---

# HTTP & WebSocket API

AETHON serves WebChat, the dashboard, and webhooks from a **single FastAPI/uvicorn
app** on one host/port (default `127.0.0.1:18790`). This page summarizes the endpoints;
for the deepest reference see
[`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md)
in the repo.

## Public endpoints (never gated)

| Method | Path | Returns |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` — liveness probe, always open (even with a dashboard token). Use this for uptime monitors. |
| `GET` | `/` | The WebChat HTML page. |

> When `dashboard.auth_token` is set, deny-by-default applies: everything except
> `/`, `/health`, `/dashboard/static/*`, and `/webhook/*` requires the token —
> including `GET /api/status` (`{"status": "running", "version": "..."}`).

## Chat

| Transport | Path | Notes |
|---|---|---|
| WebSocket | `/ws/chat` | Send plain text; receive one Markdown reply per message. Backs the WebChat UI. When a token is set it is required (with Origin validation) before the upgrade is accepted. |

## Dashboard API (gated by `dashboard.auth_token` when set)

When `dashboard.auth_token` is set, these require the token via the `aethon_dash`
cookie, `Authorization: Bearer <token>`, or `?token=<token>`:

| Method | Path | Panel |
|---|---|---|
| `GET` | `/dashboard` | Single-page dashboard app. |
| WebSocket | `/ws/dashboard` | Live dashboard updates. |
| `GET` | `/api/sessions` | Sessions. |
| `GET` | `/api/memory` | Memory entries. |
| `GET` | `/api/config` | Config dump (secrets masked to `***`). |
| `GET` | `/api/scheduler` | Scheduled jobs. |
| `GET` | `/api/telemetry` | Telemetry events / summaries. |
| `GET` | `/api/sops` | Loaded SOPs. |
| `GET` | `/api/agents` | Agents / history. |

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:18790/api/config
```

## Webhooks

Require `webhook.enabled` (default true). If `webhook.secret` is set, requests must
include `X-Aethon-Signature: <hex hmac-sha256 of the raw body>` or are rejected `403`.
Both respond `{"status":"ok","response": <agent reply text or null>}`.

| Method | Path | Body | Effect |
|---|---|---|---|
| `POST` | `/webhook/trigger` | `{"sop_name", "text", "channel"?, "recipient"?}` | Run a SOP (or plain text); optionally push the reply to a channel. |
| `POST` | `/webhook/{channel}` | `{"text": ...}` | Channel-specific inbound; response returned in the HTTP body. |

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"sop_name": "code-assist", "text": "summarize the repo"}'
```

See the **[Webhooks guide](../guides/webhooks.md)** for more examples.

## MCP

`aethon mcp` exposes the whole toolset to MCP clients (e.g. Claude Desktop) over
**stdio** — not HTTP. Approval-required tools are denied over stdio (no interactive
channel). See **[Capabilities](../concepts/capabilities.md#mcp-server--aethon-mcp)**.
