---
id: dashboard
title: Live Dashboard
sidebar_label: Live Dashboard
---

# Live Dashboard

Open **http://127.0.0.1:18790/dashboard**. The dashboard is a single-page app
(self-hosted fonts/CSS, works offline) with these panels:

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

The dashboard mounts on the WebChat app and is only available when **WebChat is
enabled** and `dashboard.enabled` is true. It also surfaces a **Features** panel
(live capability status) and **Recordings** (session replay).

## Authentication (`dashboard.auth_token`)

Empty = no auth (fine for the default localhost bind). When set, an HTTP middleware
gates `/dashboard` and the protected `/api/*` prefixes (`/api/sessions`, `/api/memory`,
`/api/config`, `/api/scheduler`, `/api/telemetry`, `/api/sops`, `/api/agents`) and
`/ws/dashboard`. Note `/api/status` and `/health` stay open. The token is accepted
(in precedence order) via the `aethon_dash` cookie, an `Authorization: Bearer <token>`
header, or a `?token=<token>` query param.

The usual flow when a token is set:

```bash
# Open once with the token; the server sets the aethon_dash cookie for you.
http://127.0.0.1:18790/dashboard?token=YOUR_TOKEN

# API calls (Bearer header):
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:18790/api/config

# WebSocket (cookie or ?token=):
ws://127.0.0.1:18790/ws/dashboard?token=YOUR_TOKEN
```

:::note Liveness/health
`GET /health` always returns `{"status": "ok"}`, even when a dashboard token is set.
:::

## Session recording & replay

When `session_recorder.enabled` is on, AETHON records the timeline + state snapshots
to a ZIP. Browse, inspect, and resume recordings from the dashboard's **Recordings**
tab. See **[Capabilities](../concepts/capabilities.md)** for the config.
