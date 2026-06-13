---
id: roadmap
title: Yol Haritası
sidebar_label: Yol Haritası
---

# Yol Haritası

**v1 (0.1.0) yayınlandı:** sağlayıcıdan bağımsız tam asistan — CLI + WebChat +
dashboard, Telegram/Discord/Slack kanalları, SQLite vektör belleği, `ask_*` devriyle
çok ajanlı uzmanlar, yerleşik ve özel SOP'lar, zamanlayıcı, webhook'lar,
telemetri, kendi model sağlayıcını getir (varsayılan OpenAI, ayrıca Anthropic / Ollama /
Bedrock / Gemini / LiteLLM / Mistral) ve Docker + CI altyapısı.

## 0.3.0 — güvenilirlik, güvenlik ve çekirdek döngü (mevcut sürüm)

- **Güvenilirlik desteği (Faz 8)** — araç çağrılarına bağlanan bir doğrulama katmanı: düzenlemede-doğrula (verify-on-edit), bir tamamlanma kapısı, girdi doğrulaması ve bir İngilizceleştirme koruması, artı kalıcı bir görev defteri (task ledger). Tüm kapılar varsayılan olarak tavsiye niteliğindedir; `reliability.strict` onları sıkı kapılara çevirir.
- **Ağ güvenliği (Faz 9A)** — paylaşılan uygulamada varsayılan-ret kimlik doğrulama, WebSocket upgrade'lerinde Origin doğrulaması, `dashboard.auth_token` olmadan **fail-closed** çalışan loopback dışı bir bağlama, mesajlaşma botlarında varsayılan-ret gönderen izin listeleri, fail-closed webhook doğrulaması, tercihe bağlı bir docker yürütme sandbox'ı (`security.sandbox: docker`) ve harici araç/webhook çıktısı için güvenilmeyen içerik işaretleme.
- **Sağlamlık ve token ekonomisi (Faz 9B)** — tek-örnek kilitleme, oturum başına tur sıralaması, geri çekilmeli (backoff) adaptör gözetimi, kalıcı zamanlamalar (ve tek seferlik hatırlatıcılar), disk-tutma (retention) budama, kullanıcıya yönelik hata yanıtları, günlük harcama tavanlı bir token sayacı (`budget.daily_usd`) ve istem-önbelleği (prompt-cache) katman sıralaması.
- **Otonom çekirdek döngü (Faz 10)** — tercihe bağlı iş alımı → plan → sınırlı yürütücü → iş kanıtı (proof-of-work) makbuzu; sıkı kaçak (runaway) korumalarıyla (yineleme üst sınırı, görev başına kalıcı deneme sınırı, bütçe tavanı). Artı bir yetenek diyeti, çalışma zamanında tanımlanan dinamik uzmanlar, okuma-ağırlıklı bir Scout uzmanı, geçmiş sıkıştırma, bir repo haritası ve tercihe bağlı bellek otomatik-anımsama (auto-recall) ile gömme-sağlamlığı.

Yukarıdakilerin tümü, aksi belirtilmedikçe **tercihe bağlı / varsayılan olarak kapalıdır**; ağ-güvenliği varsayılanları istisnadır (varsayılan olarak sıkılaştırır).

## 0.2.0 — yetenek genişlemesi

- **Yetenek araçları** — `scraper`, `use_github`, `jsonrpc`, `notify`, `manage_messages`.
- **macOS yerel** — `use_mac` + `apple_notes` (Darwin ile sınırlı; Messages/Keychain varsayılan olarak kapalı).
- **Kod zekâsı** — `lsp` aracı + otomatik tanılama kancası.
- **Dinamik araç yükleme** — alt süreç (subprocess) sandbox'ı + 3 katmanlı denetim (gating) içeren `manage_tools`.
- **Bilgisayar denetimi** — `use_computer` (tercihe bağlı, onay denetimli).
- **Ortam (ambient) / otonom mod** — proaktif boşta-zaman çalışması (tercihe bağlı).
- **Oturum kaydı ve yeniden oynatma** — kayıt (recorder) kancası + yeniden oynatma API'si + dashboard sekmesi.
- **MCP sunucusu** — `aethon mcp`, araç setini MCP istemcilerine sunar.
- **Sistem-istemi farkındalığı** — ortam / öğrenimler / son günlükler / shell geçmişi katmanları + `record_learning`.
- **Dashboard** — Features paneli + kimlik-doğru Live Company + bağlam taşması (context-overflow) koruması.

## Hâlâ ertelenenler

- Yanıt **akışı (streaming)**.
- **Ekip / pipeline orkestrasyonu** (Swarm/Graph) — çalışma zamanına bağlanması ve bir komut/araç olarak sunulması.
- **Uzman başına çok modelli** yapılandırma.
- İndekslenmiş belgeler üzerinde **erişim destekli üretim** (RAG).
- Gerçek zamanlı **ses** (STT/TTS) ve **görü (vision)** — gelecekteki bir yetenek fazına ertelendi.

Sürüm başına ayrıntılı kayıt için
[`CHANGELOG`](https://github.com/mertozbas/aethon/blob/main/CHANGELOG.md) dosyasına bakın.
