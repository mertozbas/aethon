---
id: webhooks
title: Webhooks
sidebar_label: Webhooks
---

# Webhooks

Webhooks mount on the WebChat app and require `webhook.enabled` (default true) with
WebChat enabled. Both endpoints respond `{"status":"ok","response": <agent reply text
or null>}`. If `webhook.secret` is set, requests must include
`X-Aethon-Signature: <hex hmac-sha256 of the raw body>` or they're rejected with `403`.

## Run a SOP and get the reply back

`POST /webhook/trigger`:

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"sop_name": "code-assist", "text": "summarize the repo"}'
```

## Push the reply out to another channel too

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"text": "deploy finished", "channel": "telegram", "recipient": "123456"}'
```

## Channel-specific inbound

`POST /webhook/{channel}` — the response is returned in the HTTP body:

```bash
curl -X POST http://127.0.0.1:18790/webhook/github \
  -H 'Content-Type: application/json' \
  -d '{"text": "PR #42 merged"}'
```

:::warning Verify your webhooks
Set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming
requests. Without it, anyone who can reach the port can trigger the assistant.
:::
