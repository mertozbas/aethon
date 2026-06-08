---
id: faq
title: SSS
sidebar_label: SSS
---

# SSS

### Bir API anahtarına ihtiyacım var mı?

Varsayılan OpenAI sağlayıcısı için evet — `OPENAI_API_KEY` sağlayın (veya `model.host` değerini, yerel
sunucuların genellikle yer tutucu bir anahtarı kabul ettiği OpenAI uyumlu bir uç noktaya yönlendirin).
**Hiç anahtar olmadan** çalıştırmak için tamamen yerel **Ollama** sağlayıcısını kullanın. Anthropic gibi
API sağlayıcıları da kendi anahtarlarına ihtiyaç duyar.

### AETHON verilerimi nerede saklar?

`~/.aethon` altında — yapılandırma (`config.yaml`), çalışma alanı (`workspace/`), oturumlar
(`sessions/`), günlükler (`logs/`), vektör belleği (`memory.sqlite`) ve kimlik bilgileri
(`credentials/`).

### AETHON açık kaynak mı?

PolyForm Noncommercial 1.0.0 altında **kaynağı erişilebilir** (source-available) — ticari olmayan
kullanım için ücretsizdir, ancak OSI onaylı açık kaynak **değildir** (ticari kullanıma izin verilmez).
**[Lisans](../project/license.md)** bölümüne bakın.

### Tamamen çevrimdışı / yerel olarak çalıştırabilir miyim?

Evet. `ollama` ekini (extra) kurun, `provider: ollama` ayarlayın ve bellek için Ollama gömmelerini
kullanın. Bu yapılandırmada hiçbir bulut çağrısı gerekmez.

### Web Arayüzünü ağımda nasıl yayınlarım?

`channels.webchat.host: 0.0.0.0` ayarlayın **ve ayrıca** `dashboard.auth_token` ayarlayın. Ardından
kimlik doğrulama çerezini ayarlamak için dashboard'a `?token=YOUR_TOKEN` ile erişin.

### Hangi kanallar ek kurulum gerektirir?

Yalnızca **WhatsApp** (`whatsapp` eki). CLI, WebChat, Telegram, Discord ve Slack çekirdek kurulumla
birlikte gelir.

### Kendi iş akışımı nasıl eklerim?

`~/.aethon/workspace/sops/` dizinine bir `*.sop.md` dosyası bırakın (bir `## Overview` bölümüyle) ve
onu `/<name>` olarak çağırın. **[SOP'lar](../concepts/sops.md)** bölümüne bakın.

### Asistan oturumlar arasında bir şeyler hatırlar mı?

Evet, bellek etkinleştirildiğinde. Gömmeleri SQLite içinde saklar ve onları benzerliğe göre getirir.
Bellek koruması, sırların kaydedilmesini engeller.
