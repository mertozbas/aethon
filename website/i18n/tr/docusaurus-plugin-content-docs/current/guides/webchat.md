---
id: webchat
title: Web Arayüzü (WebChat)
sidebar_label: Web Arayüzü (WebChat)
---

# Web Arayüzü (WebChat)

Tarayıcınızda **http://127.0.0.1:18790** adresini açın. Bu, bir WebSocket (`/ws/chat`)
üzerinden bağlanan ve bot yanıtlarını Markdown olarak işleyen minimal, koyu temalı bir
sohbet arayüzüdür (başlık, mesaj listesi, girdi + Gönder). Düz metin gönderirsiniz; her
mesaj için bir yanıt alırsınız.

Aynı uygulama/portta kullanışlı uç noktalar:

- `GET /api/status` → `{"status": "running", "version": "..."}` (`dashboard.auth_token` ayarlandığında korumalı).
- `GET /health` → `{"status": "ok"}` (her zaman açık, konteyner/yük dengeleyici sondaları için — uptime izleyiciler için `/api/status` yerine bunu kullanın).

Bir token ayarlandığında `/ws/chat` de token gerektirir: sohbet sayfası ilk bağlantıda token'ı
sorar (`sessionStorage`'da tutulur) ve bilinmeyen tarayıcı Origin'lerini reddeder.

## WebChat'i ağınızda yayımlama

WebChat'i localhost dışına açmak için `channels.webchat.host: 0.0.0.0` ayarlayın — **ve ayrıca**
`dashboard.auth_token` değerini de ayarlayın (bkz. **[Güvenlik](../operations/security.md)**);
loopback dışı bir bağlama bu olmadan **başlamayı reddeder**.
Dashboard, webhook'lar ve WebChat'in tümü bu tek host/portu paylaşır.

```yaml
channels:
  webchat:
    enabled: true
    host: 0.0.0.0     # expose to the network (loopback 127.0.0.1 by default)
    port: 18790
dashboard:
  auth_token: ${AETHON_DASHBOARD_TOKEN}   # required once you leave localhost
```
