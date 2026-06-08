---
id: dashboard
title: Canlı Dashboard
sidebar_label: Canlı Dashboard
---

# Canlı Dashboard

**http://127.0.0.1:18790/dashboard** adresini açın. Dashboard, şu panellere sahip tek
sayfalık bir uygulamadır (kendi barındırdığı fontlar/CSS, çevrimdışı çalışır):

| Rota | Panel |
|---|---|
| `#/overview` | Genel Bakış |
| `#/company` | Canlı Şirket (pixel-ajanlar) |
| `#/monitor` | Canlı İzleme |
| `#/sessions` | Oturumlar |
| `#/memory` | Bellek |
| `#/config` | Yapılandırma (sırlar `***` olarak maskelenir) |
| `#/logs` | Günlükler |
| `#/agents` | Ajanlar |
| `#/sops` | SOP'lar |

Dashboard, WebChat uygulamasının üzerine monte edilir ve yalnızca **WebChat etkinken**
ve `dashboard.enabled` true olduğunda kullanılabilir. Ayrıca bir **Özellikler** paneli
(canlı yetenek durumu) ve **Kayıtlar** (oturum tekrar oynatma) sunar.

## Kimlik doğrulama (`dashboard.auth_token`)

Boş = kimlik doğrulama yok (varsayılan localhost bağlaması için uygundur). Ayarlandığında,
bir HTTP ara katmanı `/dashboard` ve korumalı `/api/*` öneklerini (`/api/sessions`, `/api/memory`,
`/api/config`, `/api/scheduler`, `/api/telemetry`, `/api/sops`, `/api/agents`) ve
`/ws/dashboard` yolunu korur. `/api/status` ve `/health` yollarının açık kaldığını unutmayın.
Token (öncelik sırasına göre) `aethon_dash` çerezi, bir `Authorization: Bearer <token>`
başlığı veya bir `?token=<token>` sorgu parametresi aracılığıyla kabul edilir.

Bir token ayarlandığında olağan akış:

```bash
# Open once with the token; the server sets the aethon_dash cookie for you.
http://127.0.0.1:18790/dashboard?token=YOUR_TOKEN

# API calls (Bearer header):
curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:18790/api/config

# WebSocket (cookie or ?token=):
ws://127.0.0.1:18790/ws/dashboard?token=YOUR_TOKEN
```

:::note Canlılık/sağlık
`GET /health`, bir dashboard token'ı ayarlanmış olsa bile her zaman `{"status": "ok"}` döndürür.
:::

## Oturum kaydı ve tekrar oynatma

`session_recorder.enabled` açık olduğunda, AETHON zaman çizelgesini + durum anlık
görüntülerini bir ZIP dosyasına kaydeder. Kayıtları dashboard'ın **Kayıtlar** sekmesinden
görüntüleyin, inceleyin ve devam ettirin. Yapılandırma için bkz.
**[Yetenekler](../concepts/capabilities.md)**.
