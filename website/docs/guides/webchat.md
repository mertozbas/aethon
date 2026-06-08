---
id: webchat
title: Web UI (WebChat)
sidebar_label: Web UI (WebChat)
---

# Web UI (WebChat)

Open **http://127.0.0.1:18790** in your browser. It's a minimal dark chat UI (header,
message list, input + Send) that connects over a WebSocket (`/ws/chat`) and renders
bot replies as Markdown. You send plain text; you get one reply per message.

Useful endpoints on the same app/port:

- `GET /api/status` → `{"status": "running", "version": "..."}` (not gated).
- `GET /health` → `{"status": "ok"}` (deliberately ungated, for container/load-balancer probes).

## Exposing WebChat on your network

To expose WebChat beyond localhost, set `channels.webchat.host: 0.0.0.0` — and **also**
set `dashboard.auth_token` (see **[Security](../operations/security.md)**). The
dashboard, webhooks, and WebChat all share this one host/port.

```yaml
channels:
  webchat:
    enabled: true
    host: 0.0.0.0     # expose to the network (loopback 127.0.0.1 by default)
    port: 18790
dashboard:
  auth_token: ${AETHON_DASHBOARD_TOKEN}   # required once you leave localhost
```
