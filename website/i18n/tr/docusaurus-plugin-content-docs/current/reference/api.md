---
id: api
title: HTTP & WebSocket API
sidebar_label: HTTP API
---

# HTTP & WebSocket API

AETHON, WebChat'i, kontrol panelini ve webhook'ları tek bir ana makine/port üzerinde
**tek bir FastAPI/uvicorn uygulamasından** sunar (varsayılan `127.0.0.1:18790`). Bu sayfa
uç noktaları özetler; en ayrıntılı referans için depodaki
[`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md)
dosyasına bakın.

## Genel uç noktalar (asla kapı altında değildir)

| Method | Path | Döndürür |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` — canlılık (liveness) yoklaması, her zaman açık (kontrol paneli token'ı olsa bile). Uptime izleyicileri için bunu kullanın. |
| `GET` | `/` | WebChat HTML sayfası. |

> `dashboard.auth_token` ayarlandığında varsayılan-ret geçerlidir: `/`, `/health`,
> `/dashboard/static/*` ve `/webhook/*` dışındaki her şey token gerektirir —
> `GET /api/status` (`{"status": "running", "version": "..."}`) dâhil.

## Sohbet

| Taşıma | Path | Notlar |
|---|---|---|
| WebSocket | `/ws/chat` | Düz metin gönderin; mesaj başına bir Markdown yanıt alın. WebChat arayüzünü besler. Token ayarlandığında, upgrade kabul edilmeden önce token (Origin doğrulamasıyla) gerekir. |

## Kontrol paneli API'si (ayarlandığında `dashboard.auth_token` ile kapı altında)

`dashboard.auth_token` ayarlandığında, bunlar token'ı `aethon_dash` çerezi,
`Authorization: Bearer <token>` veya `?token=<token>` aracılığıyla gerektirir:

| Method | Path | Panel |
|---|---|---|
| `GET` | `/dashboard` | Tek sayfalık kontrol paneli uygulaması. |
| WebSocket | `/ws/dashboard` | Canlı kontrol paneli güncellemeleri. |
| `GET` | `/api/sessions` | Oturumlar. |
| `GET` | `/api/memory` | Bellek girdileri. |
| `GET` | `/api/config` | Yapılandırma dökümü (gizli değerler `***` ile maskelenir). |
| `GET` | `/api/scheduler` | Zamanlanmış işler. |
| `GET` | `/api/telemetry` | Telemetri olayları / özetleri. |
| `GET` | `/api/sops` | Yüklenen SOP'lar. |
| `GET` | `/api/agents` | Ajanlar / geçmiş. |

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:18790/api/config
```

## Webhook'lar

`webhook.enabled` gerektirir (varsayılan true). `webhook.secret` ayarlanmışsa, istekler
`X-Aethon-Signature: <ham gövdenin hex hmac-sha256 değeri>` başlığını içermelidir; aksi
halde `403` ile reddedilir. Her ikisi de `{"status":"ok","response": <ajan yanıt metni veya null>}`
döndürür.

| Method | Path | Gövde | Etki |
|---|---|---|---|
| `POST` | `/webhook/trigger` | `{"sop_name", "text", "channel"?, "recipient"?}` | Bir SOP (veya düz metin) çalıştırır; isteğe bağlı olarak yanıtı bir kanala iletir. |
| `POST` | `/webhook/{channel}` | `{"text": ...}` | Kanala özgü gelen istek; yanıt HTTP gövdesinde döndürülür. |

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"sop_name": "code-assist", "text": "summarize the repo"}'
```

Daha fazla örnek için **[Webhook'lar kılavuzu](../guides/webhooks.md)** bölümüne bakın.

## MCP

`aethon mcp`, tüm araç setini **stdio** üzerinden MCP istemcilerine (örn. Claude Desktop)
sunar — HTTP üzerinden değil. Onay gerektiren araçlar stdio üzerinden reddedilir (etkileşimli
kanal yoktur). Bkz. **[Yetenekler](../concepts/capabilities.md#mcp-server--aethon-mcp)**.
