---
id: configuration
title: Yapılandırma Referansı
sidebar_label: Yapılandırma Referansı
---

# Yapılandırma Referansı

`~/.aethon/config.yaml` dosyasının her bölümü, alan alan. **Eksik veya boş bir dosya,
tümüyle varsayılan değerlere sahip bir yapılandırma üretir.** Kavramsal kılavuz ve `${ENV_VAR}`
çözümleme kuralları için bkz. **[Yapılandırma](../getting-started/configuration.md)**.

## `model`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `provider` | str | `"openai"` | Model sağlayıcı arka ucu (openai, anthropic, ollama, bedrock, gemini, litellm, mistral, …). |
| `host` | str | `"http://localhost:11434"` | Temel URL: Ollama ana makinesi veya `provider: openai` olduğunda OpenAI uyumlu bir uç nokta. |
| `model_id` | str | `"gpt-4o"` | Model tanımlayıcısı. |
| `api_key` | str | `""` | Sağlayıcı için API anahtarı. |
| `temperature` | float | `1.0` | Örnekleme sıcaklığı. |
| `top_p` | float | `0.95` | Nucleus örnekleme olasılık kütlesi. |
| `top_k` | int | `40` | Top-k örnekleme eşiği. |
| `max_tokens` | int | `8192` | Yanıt başına üretilecek maksimum token sayısı. |
| `region` | str | `"us-west-2"` | Sağlayıcı bölgesi (örn. Bedrock tarzı arka uçlar için). |
| `extra` | dict | `{}` | Rastgele ek sağlayıcı parametreleri. |

## `channels`

**`channels.cli`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | CLI kanalını etkinleştirir. |

**`channels.webchat`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Web sohbet kanalını etkinleştirir. |
| `port` | int | `18790` | Web sohbetinin dinleme portu. |
| `host` | str | `"127.0.0.1"` | Bağlanma adresi; varsayılan olarak yalnızca loopback. Dışarıya açmak için `0.0.0.0` ayarlayın (ayrıca `dashboard.auth_token` ayarlayın). |

**`channels.telegram`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Telegram kanalını etkinleştirir. |
| `token` | str | `""` | Telegram bot token'ı. |

**`channels.discord`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Discord kanalını etkinleştirir. |
| `token` | str | `""` | Discord bot token'ı. |

**`channels.slack`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Slack kanalını etkinleştirir. |
| `bot_token` | str | `""` | Slack bot token'ı (`xoxb-…`). |
| `app_token` | str | `""` | Slack uygulama düzeyi token'ı (`xapp-…`). |

**`channels.whatsapp`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | WhatsApp kanalını etkinleştirir (deneysel; başka alan yok). |

## `security`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `workspace_only` | bool | `false` | true olduğunda, dosya araçlarını `~/.aethon/workspace` ile sınırlar; false olduğunda (varsayılan), engellenen sistem/kimlik bilgisi yolları dışında `$HOME` altındaki her yere izin verir. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Ayrılmıştır; şu anda uygulanmaz. Onay kapısı `approval` bölümünde yapılandırılır. |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Engellenen kabuk komutu alt dizeleri. |
| `allowed_senders` | dict[str, list[str]] | `{}` | Kanal bazında gönderen tanımlayıcısı izin listesi. |

## `session`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `storage_dir` | str | `"~/.aethon/sessions"` | Oturum durumunun saklandığı dizin. |
| `conversation_manager` | str | `"summarizing"` | Konuşma yöneticisi stratejisi. |
| `summary_ratio` | float | `0.3` | Sıkıştırma sırasında özetlenecek geçmiş oranı. |
| `preserve_recent_messages` | int | `10` | Aynen korunan son mesaj sayısı. |

## `memory`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Vektör belleğini etkinleştirir. |
| `embedding_provider` | str | `"ollama"` | Gömme (embedding) sağlayıcısı (ollama, openai). |
| `embedding_model` | str | `"nomic-embed-text"` | Gömme modeli adı. |
| `embedding_api_key` | str | `""` | Gömme sağlayıcısı için API anahtarı. |
| `db_path` | str | `"~/.aethon/memory.sqlite"` | Vektör deposu için SQLite yolu. |

## `multi_agent`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Çok ajanlı sistemi etkinleştirir. |
| `max_handoffs` | int | `10` | Maksimum ajandan ajana devir sayısı. |
| `max_iterations` | int | `10` | Çalıştırma başına maksimum yineleme sayısı. |
| `execution_timeout` | float | `300.0` | Genel çalıştırma zaman aşımı (saniye). |
| `node_timeout` | float | `120.0` | Düğüm başına zaman aşımı (saniye). |

## `sops`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | SOP yürütmesini etkinleştirir. |
| `builtin_sops_enabled` | bool | `true` | Yerleşik SOP'ları etkinleştirir. |

## `approval`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Kesinti tabanlı onay hook'unu etkinleştirir. |
| `requires_approval` | list[str] | `["shell", "file_write"]` | Bu hook üzerinden onay gerektiren eylem türleri. |

## `telemetry`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Telemetri hook'unu etkinleştirir. |
| `max_history` | int | `10000` | Saklanan maksimum telemetri olayı sayısı. |

## `memory_guard`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Bellek koruma (memory guard) hook'unu etkinleştirir. |
| `custom_patterns` | list[str] | `[]` | Korumanın yakalaması gereken ek desenler. |

## `scheduler`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Zamanlayıcıyı etkinleştirir. |
| `default_channel` | str | `"cli"` | Zamanlanmış çıktılar için varsayılan kanal. |
| `jobs` | dict | `{}` | Zamanlanmış iş tanımları. |

## `dashboard`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Web kontrol panelini etkinleştirir. |
| `pixel_agents` | bool | `true` | Pixel-agents görselleştirmesini etkinleştirir. |
| `auth_token` | str | `""` | İsteğe bağlı paylaşılan token; boş = kimlik doğrulama yok. `/dashboard` ile korumalı `/api/*` + `/ws/dashboard` uç noktalarını `?token=`, `Authorization: Bearer` veya `aethon_dash` çerezi üzerinden korur. |

## `webhook`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Webhook uç noktasını etkinleştirir. |
| `secret` | str | `""` | Gelen webhook'ları doğrulamak için paylaşılan gizli anahtar (HMAC-SHA256). |

## `mcp`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | MCP sunucu entegrasyonunu etkinleştirir. |
| `servers` | list[dict] | `[]` | MCP sunucu tanımlarının listesi. |

## `performance`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `model_warmup` | bool | `false` | İlk mesaj gecikmesini azaltmak için açılışta gerçek bir model isteği gönderir (varsayılan olarak kapalı; kota harcar). |
| `session_cache_size` | int | `10` | Bellekte önbelleğe alınan oturum sayısı. |
| `embedding_cache_size` | int | `100` | Önbelleğe alınan gömme (embedding) sayısı. |
| `max_tool_output_chars` | int | `12000` | Tek bir araç sonucunun bağlamı taşırmaması için üst sınır (`0` = kapalı). |

## `paths`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `workspace` | str | `"~/.aethon/workspace"` | Çalışma alanı kök dizini. |
| `sessions` | str | `"~/.aethon/sessions"` | Oturumlar dizini. |
| `memory_db` | str | `"~/.aethon/memory.sqlite"` | Vektör belleği SQLite yolu. |
| `logs` | str | `"~/.aethon/logs"` | Günlükler dizini. |
| `credentials` | str | `"~/.aethon/credentials"` | Kimlik bilgileri dizini. |
| `recordings` | str | `"~/.aethon/recordings"` | Oturum kayıtları dizini. |

:::note
Yol değeri içeren alanlardaki `~` karakteri olduğu gibi saklanır; yalnızca yapılandırma
dosyasının kendi yolu için `load()`/`write()` içinde genişletilir. Bazı değerler bilinçli
olarak örtüşür (örn. `memory.db_path` ve `paths.memory_db` her ikisi de varsayılan olarak
`~/.aethon/memory.sqlite`; `session.storage_dir` ve `paths.sessions` her ikisi de
`~/.aethon/sessions`).
:::

İsteğe bağlı (opt-in) `capabilities`, `macos`, `lsp`, `runtime_tools`, `session_recorder`,
`ambient` ve `prompt` blokları için bkz. **[Yapılandırma](../getting-started/configuration.md#capabilities--runtime-features-opt-in)**
ve **[Yetenekler](../concepts/capabilities.md)**.
