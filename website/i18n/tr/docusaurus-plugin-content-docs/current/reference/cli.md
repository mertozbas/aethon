---
id: cli
title: CLI Referansı
sidebar_label: CLI Referansı
---

# CLI Referansı

```bash
aethon [--version] <command> [options]
```

| Komut | Açıklama | Seçenekler |
|---|---|---|
| `aethon init` | AETHON'u kurar (sağlayıcı menüsü openai/anthropic/ollama, model, bellek, mesajlaşma botları) ve yapılandırma dosyasını yazar. | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`); `--force` (mevcut bir yapılandırmayı sormadan üzerine yazar). |
| `aethon doctor` | Geçerli yapılandırmayı ve sağlayıcı kullanılabilirliğini teşhis eder (sağlayıcı/model, sağlayıcı kontrolü, bellek). | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`). |
| `aethon start` | AETHON'u başlatır (yapılandırma yoksa önce kurulum sihirbazını çalıştırır; ağ geçidini ve etkin tüm kanalları başlatır). | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`). |
| `aethon mcp` | AETHON'un tüm araç setini stdio üzerinden MCP istemcilerine (örn. Claude Desktop) sunar. Bilgilendirme çıktısı stderr'e gider. | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`). |
| `aethon --version` | `aethon, version 0.2.0` yazdırır ve çıkar. | — |

`launcher-macos` ekstrasıyla birlikte ayrıca kurulur: **`aethon-menubar`** — bir macOS
menü çubuğu başlatıcısı (Sunucuyu Başlat/Durdur, WebChat'i aç, ayarlar).
