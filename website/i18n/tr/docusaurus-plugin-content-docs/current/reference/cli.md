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
| `aethon doctor` | Geçerli yapılandırmayı ve sağlayıcı kullanılabilirliğini teşhis eder (sağlayıcı/model, sağlayıcı kontrolü, bellek), artı disk-kullanımı/tutma (retention), bilinmeyen yapılandırma anahtarları, yol izinleri ve sır-hijyeni uyarıları. | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`). |
| `aethon start` | AETHON'u başlatır (yapılandırma yoksa önce kurulum sihirbazını çalıştırır; ağ geçidini ve etkin tüm kanalları başlatır). `--insecure-bind` verilmedikçe, `dashboard.auth_token` olmadan loopback dışı bir bağlamayı reddeder. | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`); `--insecure-bind` (`dashboard.auth_token` olmadan loopback dışı bir bağlamaya izin verir — yalnızca kendi kimlik doğrulayan ters proxy'nizin arkasında). |
| `aethon backup` | `~/.aethon` dizinini canlı-güvenli bir `.tar.gz` dosyasına yedekler (SQLite deposunu güvenli biçimde ele alır; `logs/` dizinini atlar). | `--output, -o <path>` (varsayılan `~/.aethon-backup-<timestamp>.tar.gz`). |
| `aethon service install` | Açılışta çalışan bir hizmet kurar: macOS'ta bir launchd ajanı, Linux'ta bir systemd **kullanıcı** birimi. Etkinleştirme komutunu yazdırır. | — |
| `aethon mcp` | AETHON'un tüm araç setini stdio üzerinden MCP istemcilerine (örn. Claude Desktop) sunar. Bilgilendirme çıktısı stderr'e gider. | `--config, -c <path>` (varsayılan `~/.aethon/config.yaml`). |
| `aethon --version` | `aethon, version <paket sürümü>` yazdırır ve çıkar. | — |

`launcher-macos` ekstrasıyla birlikte ayrıca kurulur: **`aethon-menubar`** — bir macOS
menü çubuğu başlatıcısı (Sunucuyu Başlat/Durdur, WebChat'i aç, ayarlar).
