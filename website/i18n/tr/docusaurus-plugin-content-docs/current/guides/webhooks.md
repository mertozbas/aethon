---
id: webhooks
title: Webhook'lar
sidebar_label: Webhook'lar
---

# Webhook'lar

Webhook'lar WebChat uygulamasının üzerine monte edilir ve WebChat etkinken
`webhook.enabled` (varsayılan true) gerektirir. Her iki uç nokta da
`{"status":"ok","response": <ajan yanıt metni veya null>}` yanıtını verir.
`webhook.secret` ayarlanmışsa, isteklerin `X-Aethon-Signature: <ham gövdenin hex hmac-sha256'sı>`
içermesi gerekir; aksi takdirde `403` ile reddedilir.

## Bir SOP çalıştırın ve yanıtı geri alın

`POST /webhook/trigger`:

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"sop_name": "code-assist", "text": "summarize the repo"}'
```

## Yanıtı ayrıca başka bir kanala da gönderin

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H 'Content-Type: application/json' \
  -d '{"text": "deploy finished", "channel": "telegram", "recipient": "123456"}'
```

## Kanala özgü gelen istekler

`POST /webhook/{channel}` — yanıt HTTP gövdesinde döndürülür:

```bash
curl -X POST http://127.0.0.1:18790/webhook/github \
  -H 'Content-Type: application/json' \
  -d '{"text": "PR #42 merged"}'
```

:::warning Webhook'larınızı doğrulayın
Gelen isteklerde bir HMAC-SHA256 `X-Aethon-Signature` zorunlu kılmak için `webhook.secret`
değerini ayarlayın. Bu olmadan, porta ulaşabilen herkes asistanı tetikleyebilir.
:::
