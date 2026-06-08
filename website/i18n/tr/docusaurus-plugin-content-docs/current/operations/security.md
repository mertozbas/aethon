---
id: security
title: Güvenlik
sidebar_label: Güvenlik
---

# Güvenlik

AETHON **yerel öncelikli**dir ve güvenli varsayılanlarla gelir:

- **Loopback bağlama:** WebChat (ve onun üzerine bağlanan dashboard/webhook'lar) varsayılan olarak `127.0.0.1` adresine bağlanır. localhost'un ötesine açmak için `channels.webchat.host: 0.0.0.0` **ve** bir `dashboard.auth_token` ayarlayın.
- **Dashboard kimlik doğrulama token'ı:** `dashboard.auth_token` ayarlandığında, `/dashboard`, korumalı `/api/*` önekleri ve `/ws/dashboard` token gerektirir (`aethon_dash` çerezi, `Authorization: Bearer` veya `?token=` aracılığıyla). `/api/status` ve `/health` ise sağlık denetimleri (probe) için açık kalır.
- **Dosya erişimi sandbox'ı:** varsayılan olarak dosya araçları, sistem ve kimlik bilgisi yollarından oluşan bir engelleme listesi (`/etc`, `/usr`, `/bin`, `~/.ssh`, `~/.gnupg`, `~/.aethon/credentials`, …) **dışında** ev dizininizin altındaki her yeri okuyup yazabilir. Dosya araçlarını yalnızca `~/.aethon/workspace` ile sınırlamak için `security.workspace_only: true` ayarlayın.
- **Engellenen komutlar:** güvenlik kancası (hook), herhangi bir `security.blocked_commands` girdisini içeren shell komutlarını reddeder (varsayılan `rm -rf /`, `sudo`, `mkfs` ve yerleşik bir tehlike listesi).
- **Onay denetimi (gating):** isteğe bağlı, kesme (interrupt) tabanlı bir kanca, `approval.requires_approval` içindeki eylemler için onay gerektirebilir (varsayılan `shell`, `file_write`) — **varsayılan olarak kapalıdır** (`approval.enabled: false`). *(`security.require_approval` alanı ayrılmıştır ve şu anda uygulanmamaktadır.)*
- **Gönderen izin listeleri:** `security.allowed_senders`, her kanala kimin mesaj gönderebileceğini kısıtlayabilir.
- **Sır maskeleme:** dashboard'daki `GET /api/config` dökümü, hassas anahtarları (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) `***` olarak maskeler.
- **Bellek koruması:** bellek koruma (memory guard) kancası, sırların uzun süreli belleğe yazılmasını engeller.
- **Webhook doğrulaması:** gelen webhook'larda HMAC-SHA256 `X-Aethon-Signature` zorunlu kılmak için `webhook.secret` ayarlayın.
- **Kimlik bilgisi yalıtımı:** token'ları yapılandırma dosyasının dışında tutmak için `${ENV_VAR}` referansları kullanın ve sırları `~/.aethon/credentials/` altında saklayın.

:::warning Dışarıya açmadan önce
`channels.webchat.host: 0.0.0.0` ayarladığınız an, bir `dashboard.auth_token` da ayarlayın —
aksi takdirde porta erişebilen herkes dashboard + API'ye tam erişim kazanır.
:::

Tam güvenlik modeli ve tehdit analizi için depodaki
[`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md)
ve [`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) dosyalarına bakın.
