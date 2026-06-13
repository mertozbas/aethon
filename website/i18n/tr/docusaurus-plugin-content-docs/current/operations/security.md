---
id: security
title: Güvenlik
sidebar_label: Güvenlik
---

# Güvenlik

AETHON **yerel öncelikli**dir ve güvenli varsayılanlarla gelir:

- **Loopback bağlama (fail-closed):** WebChat (ve onun üzerine bağlanan dashboard/webhook'lar) varsayılan olarak `127.0.0.1` adresine bağlanır. localhost'un ötesine açmak için `channels.webchat.host: 0.0.0.0` **ve** bir `dashboard.auth_token` ayarlayın — loopback dışı bir bağlama, token olmadan **başlamayı reddeder** (yalnız kendi kimlik doğrulayan proxy'nizin arkasında `--insecure-bind` ile geçersiz kılınır).
- **Paylaşılan kimlik doğrulama token'ı (varsayılan ret):** `dashboard.auth_token` ayarlandığında, paylaşılan uygulamadaki **tüm** yollar token gerektirir — her `/api/*` (`/api/status` dâhil), `/dashboard`, FastAPI belgeleri ve bilinmeyen yollar (401). Genel istisnalar: `/`, `/health`, `/dashboard/static/*` ve kendi HMAC'iyle doğrulanan `/webhook/*`. Her iki WebSocket de (`/ws/chat`, `/ws/dashboard`) upgrade'i kabul etmeden önce Origin başlığını ve token'ı doğrular. Token, `aethon_dash` çerezi, `Authorization: Bearer` veya `?token=` aracılığıyla verilir. Uptime denetimleri için `/api/status` yerine (artık korumalı) gerçekten açık olan `/health`'i kullanın.
- **Dosya erişimi sandbox'ı:** varsayılan olarak dosya araçları, sistem ve kimlik bilgisi yollarından oluşan bir engelleme listesi (`/etc`, `/usr`, `/bin`, `~/.ssh`, `~/.gnupg`, `~/.aethon/credentials`, …) **dışında** ev dizininizin altındaki her yeri okuyup yazabilir. Dosya araçlarını yalnızca `~/.aethon/workspace` ile sınırlamak için `security.workspace_only: true` ayarlayın.
- **Engellenen komutlar:** güvenlik kancası (hook), herhangi bir `security.blocked_commands` girdisini içeren shell komutlarını reddeder (varsayılan `rm -rf /`, `sudo`, `mkfs` ve yerleşik bir tehlike listesi).
- **Onay denetimi (gating):** isteğe bağlı, kesme (interrupt) tabanlı bir kanca, `approval.requires_approval` içindeki eylemler için onay gerektirebilir (varsayılan `shell`, `file_write`, `manage_tools`, `manage_specialists`) — **varsayılan olarak kapalıdır** (`approval.enabled: false`). *(`security.require_approval` alanı ayrılmıştır ve şu anda uygulanmamaktadır.)*
- **Gönderen izin listeleri (varsayılan ret):** `security.allowed_senders.<kanal>`, her kanala kimin mesaj gönderebileceğini kısıtlar. Mesajlaşma botlarında (`telegram`/`discord`/`slack`/`whatsapp`) **boş bir izin listesi herkesi reddeder** — botu kullanmak için izin verilen gönderen kimliklerini ekleyin.
- **Yürütme sandbox'ı (tercihe bağlı):** `shell` aracını, kaynak üst sınırları (`sandbox_memory`, `sandbox_cpus`, `sandbox_pids_limit`), varsayılan olarak host ağı olmadan (`sandbox_network: none`) ve salt okunur bir rootfs ile oturum başına tek kullanımlık bir container içinde çalıştırmak için `security.sandbox: docker` ayarlayın. `docker` seçilip kullanılamıyorsa **başlamayı reddeder** (fail closed). Varsayılan `none`, shell'i host üzerinde engellenen-komutlar listesi altında çalıştırır. *(Dosya araçları bu sürümde host tarafında kalır.)*
- **Güvenilmeyen içerik işaretleme (varsayılan olarak açık):** `security.mark_untrusted_content: true` ile, harici içerik araçlarının (`scraper`, `http_request`, `jsonrpc`, `use_github`) sonuçları ve gelen webhook yükleri `[UNTRUSTED EXTERNAL CONTENT]` işaretleriyle sarmalanır; böylece model bunları talimat değil veri olarak ele alır. Bu, bir enjeksiyon dedektörü değil **dürüst bir işaretlemedir** — devre dışı bırakmak için `false` yapın.
- **Sır maskeleme:** dashboard'daki `GET /api/config` dökümü, hassas anahtarları (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) `***` olarak maskeler.
- **Bellek koruması:** bellek koruma (memory guard) kancası, sırların uzun süreli belleğe yazılmasını engeller.
- **Webhook doğrulaması (fail-closed):** gelen webhook'larda HMAC-SHA256 `X-Aethon-Signature` zorunlu kılmak için `webhook.secret` ayarlayın. Loopback dışı bir bağlamada boş bir secret ile `/webhook/*` yolları hiç kaydedilmez.
- **Kimlik bilgisi yalıtımı:** token'ları yapılandırma dosyasının dışında tutmak için `${ENV_VAR}` referansları kullanın ve sırları `~/.aethon/credentials/` altında saklayın.

:::warning Dışarıya açmadan önce
`channels.webchat.host: 0.0.0.0` ayarladığınız an, bir `dashboard.auth_token` da ayarlayın —
aksi takdirde porta erişebilen herkes dashboard + API'ye tam erişim kazanır.
:::

Tam güvenlik modeli ve tehdit analizi için depodaki
[`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) dosyasına bakın.
