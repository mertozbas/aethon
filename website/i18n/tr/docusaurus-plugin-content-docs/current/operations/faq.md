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

### Bir API sağlayıcısı büyük bir fatura çıkarabilir mi?

Günlük harcamayı sınırlamak için `budget.daily_usd` ayarlayın. Her turun token kullanımı ölçülür ve
fiyatlandırılır (yerleşik fiyat tablosunu `budget.pricing` ile geçersiz kılabilirsiniz); harcama,
tavanın `budget.warn_ratio` (varsayılan `0.8`) oranını aştığında turlar bir kez **uyarılır** ve tavan
aşıldığında **engellenir** — bu, ortam (ambient) ve zamanlayıcı turlarını da durdurur. Varsayılan `0.0`,
sınırsız anlamına gelir (yalnızca ölç). Bulut harcamasından tamamen kaçınmak için Ollama ile tümüyle
yerel çalışın.

### Asistan oturumlar arasında bir şeyler hatırlar mı?

Evet, bellek etkinleştirildiğinde. Gömmeleri SQLite içinde saklar ve onları benzerliğe göre getirir.
Bellek koruması, sırların kaydedilmesini engeller. `memory.auto_recall` açıkken (tercihe bağlı,
varsayılan olarak kapalı), her tur gelen mesajı gömer ve en iyi eşleşen uzun süreli bellekleri bir istem
katmanı olarak enjekte eder; böylece ajan bellek aracını çağırmadan ilgili bellekler yüzeye çıkar. Vektör
belleği ayrıca her satırın gömme modelini ve boyutunu kaydeder ve boyutları karıştırmayı reddeder;
böylece gömme modelini değiştirmek, benzerlik aramasını sessizce bozamaz.
