---
id: intro
title: AETHON Nedir?
sidebar_label: Giriş
slug: /intro
---

# AETHON Nedir?

> **Kendi model sağlayıcınızı getirin.** AETHON sağlayıcıdan bağımsızdır: onu
> **OpenAI API**'sine (varsayılan) ya da **OpenAI uyumlu herhangi bir uç noktaya**
> (vLLM, LM Studio, LocalAI veya OpenAI API'sini konuşan herhangi bir servis),
> **Anthropic API**'sine veya tamamen yerel bir **Ollama** modeline yönlendirin —
> ayrıca **Bedrock, Gemini, LiteLLM ve Mistral**'ı da destekler. Onu siz
> çalıştırırsınız; arka ucu siz seçersiniz.

AETHON, **kendiniz çalıştırdığınız kişisel bir yapay zekâ asistanıdır**. Kalıcı,
bellek destekli tek bir asistanla konuşmak için ihtiyaç duyduğunuz her giriş
noktasını içeren tek bir Python paketidir:

- etkileşimli sohbet için bir **terminal CLI**,
- tarayıcınızda bir **Web Arayüzü (WebChat)**,
- Telegram, Discord, Slack ve (deneysel olarak) WhatsApp için **mesajlaşma botları**,
- oturumları, belleği, telemetriyi, ajanları ve SOP'leri gerçek zamanlı izlemek için bir **canlı pano**,
- başka sistemlerin asistanı tetikleyebilmesi için **webhook'lar**,
- ve asistanın işleri bir zaman çizelgesine göre çalıştırabilmesi için bir **cron zamanlayıcı**.

AETHON, arka planda **Strands Agents SDK** üzerine kuruludur. Ana orkestratör
ajanı, görevleri **uzman alt ajanlara** (Coder, Researcher, Analyst, Planner)
devredebilir, sizin için önemli olan şeyleri **uzun süreli vektör belleğinde**
tutabilir, **SOP'leri** (Standart İşletim Prosedürleri — yeniden kullanılabilir,
slash ile çağrılan iş akışları) izleyebilir ve **araçlar** (dosyalar, kabuk,
zamanlama, mesajlaşma, MCP sunucuları) çağırabilir.

**Model sağlayıcısını siz getirirsiniz.** AETHON varsayılan olarak **OpenAI**
(`gpt-4o`) kullanır: resmi OpenAI API'si için bir `api_key` ayarlayın ya da `host`
değerini **OpenAI uyumlu herhangi bir uç noktaya** yönlendirin — vLLM, LM Studio
veya LocalAI gibi yerel bir sunucu ya da OpenAI API'sini konuşan herhangi bir
servis. Her şey **yerel öncelikli** olduğu için (servisler varsayılan olarak
`127.0.0.1` adresine bağlanır ve verileriniz `~/.aethon` altında durur),
verilerinizin ve faturanızın kontrolü sizde kalır.

:::tip Tasarımı gereği sağlayıcıdan bağımsız
Yapılandırmanızda tek bir satırı (`model.provider`) değiştirerek OpenAI, Anthropic
API, tamamen yerel bir Ollama modeli, Bedrock, Gemini, LiteLLM veya Mistral arasında
geçiş yapın.
:::

| | |
|---|---|
| **Yazar** | Mert Özbaş |
| **Depo** | [github.com/mertozbas/aethon](https://github.com/mertozbas/aethon) |
| **Sürüm** | 0.2.0 |
| **Lisans** | PolyForm Noncommercial 1.0.0 (kaynak erişilebilir; ticari olmayan kullanım için ücretsiz) |

---

## Özellik turu

### Model arka uçları
- **Kendi sağlayıcınızı getirin** — bir API anahtarıyla varsayılan olarak **OpenAI** (`gpt-4o`), **ya da** OpenAI uyumlu herhangi bir **base URL** (vLLM, LM Studio, LocalAI, …).
- **Herhangi bir Strands sağlayıcısıyla** çalışır: `openai` (varsayılan), `anthropic`, `ollama`, `bedrock`, `gemini`, `litellm`, `mistral` (ayrıca test için `fake`/`echo`).
- Ollama ile **tamamen yerel** çalıştırın — API anahtarı yok, bulut çağrısı yok.
- Rehberli **kurulum sihirbazı** (`aethon init`) ve bir **tanılama** komutu (`aethon doctor`).

### Kanallar (hepsi tek pakette)
- **CLI** — geçmiş ve Markdown render desteğiyle terminal sohbeti.
- **WebChat** — FastAPI/uvicorn tarafından sunulan bir tarayıcı sohbet arayüzü.
- **Telegram, Discord, Slack** — mesajlaşma botları (kütüphaneler çekirdek kurulumla birlikte gelir).
- **WhatsApp** — deneysel, isteğe bağlı `whatsapp` ekstrasıyla.

### Asistan zekâsı
- **Uzun süreli vektör belleği** — kosinüs benzerliği aramalı, SQLite destekli gömme (embedding) vektörleri.
- **Çok ajanlı uzmanlar** — Coder, Researcher, Analyst, Planner; ana ajandan `ask_*` devretme araçlarıyla erişilebilir.
- **SOP'ler** — yerleşik `/code-assist`, `/pdd`, `/codebase-summary`, ayrıca kendi özel `*.sop.md` iş akışlarınız.
- **Çalışma alanı kişilik dosyaları** — `SOUL.md`, `TOOLS.md`, `CONTEXT.md` kimliği, tercihleri ve canlı durumu tanımlar.
- **Çekirdek araçlar** — dosya okuma/yazma/düzenleme, kabuk, zamanlama, bağlam güncellemeleri, mesajlaşma ve MCP araçları.
- **Kendini geliştirme** — `record_learning` keşifleri `LEARNINGS.md`'ye kalıcı olarak kaydeder; sistem istemi **ortam farkındalıdır** (OS/cwd/kabuk).

### Yetenekler (tercihe bağlı araçlar)
- **Web ve API'ler** — `scraper` (BeautifulSoup), `use_github` (GitHub GraphQL), `jsonrpc` (HTTP/WebSocket), `notify` (yerel bildirimler).
- **macOS yerel** — `use_mac` (Calendar, Reminders, Mail, Contacts, Safari, Finder, Shortcuts, Messages, Music, Keychain) ve `apple_notes`; Darwin'e özgü, Messages/Keychain varsayılan olarak kapalı.
- **Kod zekâsı** — `lsp` (pyright/gopls/… aracılığıyla tanılama, tanıma git, referanslar, hover) ve otomatik tanılama kancası.
- **Dinamik araçlar** — `manage_tools` çalışma zamanında bir alt süreç sandbox'ında araç yükler/oluşturur (kapılı).
- **Bilgisayar kontrolü** — `use_computer` (ekran/fare/klavye, yüksek riskli, varsayılan olarak kapalı, onay kapılı).
- **Ortam / otonom mod** — proaktif boş zaman çalışması, tamamen tercihe bağlı.
- **İç gözlem** — `manage_messages` ajanın kendi konuşmasını turdan haberdar şekilde inceler.

### Operasyonlar ve görünürlük
- **Canlı pano** — genel bakış, Özellikler (yetenek durumu), canlı şirket (pixel-agents), canlı izleyici, oturumlar, kayıtlar (oturum tekrarı), bellek, yapılandırma, loglar, ajanlar, SOP'ler.
- **Oturum kaydı ve tekrarı** — zaman çizelgesini + durum anlık görüntülerini bir ZIP'e kaydedin; panodan göz atın ve devam edin.
- **MCP sunucusu** — `aethon mcp`, AETHON'un tüm araç setini stdio üzerinden MCP istemcilerine (ör. Claude Desktop) sunar.
- **Zamanlayıcı** — SOP'leri çalıştıran ve sonuçları bir kanala ileten cron işleri.
- **Webhook'lar** — isteğe bağlı HMAC-SHA256 doğrulamasıyla `POST /webhook/trigger` ve `POST /webhook/{channel}`.
- **Telemetri** — panoda özetlerle gösterilen olay geçmişi.
- **Bağlam güvenliği** — aşırı büyük araç çıktısı otomatik olarak sınırlanır; böylece tek bir devasa komut model bağlamını taşıramaz.

### Güvenlik ve gizlilik
- **Yerel öncelikli**: servisler varsayılan olarak `127.0.0.1` adresine bağlanır; verileriniz `~/.aethon` içinde durur.
- **Çalışma alanı sınırı** + **engellenen komut** filtreleme + **onay** kancaları.
- **Pano kimlik doğrulama jetonu**, API yapılandırma dökümlerinde **gizli maskeleme** ve gizli bilgileri uzun süreli bellekten uzak tutan bir **bellek koruyucusu**.

:::info 0.2.0'da yeni
Yetenek araçları (web/GitHub/JSON-RPC/notify), macOS yerel araçları, LSP,
sandbox'lanmış dinamik araçlar, ortam modu, oturum kaydı/tekrarı ve bir MCP
sunucusu. Tam başvuru: **[Yetenekler](./concepts/capabilities.md)**.
:::

---

## Şimdi nereye?

- **Yeni misiniz?** Eksiksiz bir ilk kullanım rehberi için **[Kurulum](./getting-started/installation.md)** sayfasına, ardından **[Yapılandırma](./getting-started/configuration.md)** sayfasına gidin.
- **Model mi seçiyorsunuz?** **[Model Arka Uçları](./getting-started/model-backends.md)** sayfasına bakın.
- **Büyük resmi mi görmek istiyorsunuz?** **[Mimari](./reference/architecture.md)** sayfasını okuyun.
