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

## 0.2.0 — yetenek genişlemesi (mevcut sürüm)

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
- Gerçek zamanlı **ses** (STT/TTS).

Ayrıntılar için
[`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md)
dosyasına bakın.
