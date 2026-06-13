---
id: configuration
title: Yapılandırma Referansı
sidebar_label: Yapılandırma Referansı
---

# Yapılandırma Referansı

`~/.aethon/config.yaml` dosyasının bölümleri, alan alan. **Eksik veya boş bir dosya,
tümüyle varsayılan değerlere sahip bir yapılandırma üretir.** Tercihe bağlı (opt-in)
`capabilities`, `macos`, `lsp`, `runtime_tools`, `session_recorder`, `ambient` ve `prompt`
blokları, kavramsal kılavuzda ele alınır (aşağıda bağlantılı). O kılavuz ve `${ENV_VAR}`
çözümleme kuralları için bkz. **[Yapılandırma](../getting-started/configuration.md)**.

## `model`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `provider` | str | `"openai"` | Model sağlayıcı arka ucu (openai, anthropic, ollama, bedrock, gemini, litellm, mistral, …) veya çevrimdışı hazır-yanıt arka ucu için `fake`/`echo` (ağ yok; testlerde kullanılır). |
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
| `allowed_origins` | list[str] | `[]` | WS upgrade'lerinde kabul edilen ek tarayıcı Origin'leri (tam origin'ler, ör. `https://chat.example.com`). Boş = yalnızca aynı host. |

**`channels.telegram`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Telegram kanalını etkinleştirir. |
| `token` | str | `""` | Telegram bot token'ı. |
| `chat_id` | str | `""` | Proaktif/giden gönderimler için varsayılan hedef (zamanlayıcı, `send_message`, bildirimler). Tepkisel yanıtlar bunu yok sayar. |

**`channels.discord`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Discord kanalını etkinleştirir. |
| `token` | str | `""` | Discord bot token'ı. |
| `channel_id` | str | `""` | Proaktif/giden gönderimler için varsayılan hedef (kanal kimliği veya DM için kullanıcı kimliği). Tepkisel yanıtlar bunu yok sayar. |

**`channels.slack`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Slack kanalını etkinleştirir. |
| `bot_token` | str | `""` | Slack bot token'ı (`xoxb-…`). |
| `app_token` | str | `""` | Slack uygulama düzeyi token'ı (`xapp-…`). |
| `channel` | str | `""` | Proaktif/giden gönderimler için varsayılan hedef (kanal kimliği `C…`, kullanıcı kimliği `U…` veya kanal adı). Tepkisel yanıtlar bunu yok sayar. |

**`channels.whatsapp`**

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | WhatsApp kanalını etkinleştirir (deneysel). |
| `chat` | str | `""` | Proaktif/giden gönderimler için varsayılan hedef (telefon numarası / sohbet kullanıcı kimliği). Tepkisel yanıtlar bunu yok sayar. |

## `security`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `bypass_tool_consent` | bool | `true` | Araçları, araç başına onay istemi olmadan çalıştırır (AETHON başsız çalışır ve kendi koruma bariyerlerine sahiptir). Araç başına istemleri geri getirmek için `false` ayarlayın. |
| `workspace_only` | bool | `false` | true olduğunda, dosya araçlarını `~/.aethon/workspace` ile sınırlar; false olduğunda (varsayılan), engellenen sistem/kimlik bilgisi yolları dışında `$HOME` altındaki her yere izin verir. |
| `require_approval` | list[str] | `["shell", "file_write", "send_message"]` | Ayrılmıştır; şu anda uygulanmaz. Onay kapısı `approval` bölümünde yapılandırılır. |
| `blocked_commands` | list[str] | `["rm -rf /", "sudo", "mkfs"]` | Engellenen kabuk komutu alt dizeleri. |
| `allowed_senders` | dict[str, list[str]] | `{}` | Kanal bazında gönderen tanımlayıcısı izin listesi (bir mesajlaşma botunda boş liste = herkesi reddeder). |
| `mark_untrusted_content` | bool | `true` | Harici içerik araçlarının (`scraper`/`http_request`/`jsonrpc`/`use_github`) sonuçlarını ve webhook yüklerini `[UNTRUSTED EXTERNAL CONTENT]` işaretleriyle sarmalar (bir enjeksiyon dedektörü değil, dürüst bir işaretleme). |
| `sandbox` | str | `"none"` | `none` = shell, host üzerinde engelleme listesi altında çalışır; `docker` = shell, oturum başına bir container içinde çalışır (docker kullanılamıyorsa fail closed). |
| `sandbox_image` | str | `"python:3.12-slim"` | docker sandbox'ı için container imajı. |
| `sandbox_network` | str | `"none"` | `docker --network`; `none` = host/ağ erişimi yok. |
| `sandbox_memory` | str | `"512m"` | `docker --memory` üst sınırı. |
| `sandbox_cpus` | str | `"1.0"` | `docker --cpus` üst sınırı. |
| `sandbox_pids_limit` | int | `256` | `docker --pids-limit` üst sınırı. |
| `sandbox_timeout` | int | `60` | Sandbox'taki shell komutu başına saniye. |
| `sandbox_read_only` | bool | `true` | Salt okunur container rootfs'i (yazılabilir `/tmp` + çalışma alanı bağlaması). |

## `session`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `storage_dir` | str | `"~/.aethon/sessions"` | Oturum durumunun saklandığı dizin. |
| `conversation_manager` | str | `"summarizing"` | Konuşma yöneticisi stratejisi. |
| `summary_ratio` | float | `0.3` | Sıkıştırma sırasında özetlenecek geçmiş oranı. |
| `preserve_recent_messages` | int | `10` | Aynen korunan son mesaj sayısı. |
| `compact_enabled` | bool | `false` | Model girdisindeki eski, büyük araç çıktılarını kompakt bir işaretçiyle değiştirir (bellekte; diskteki denetim izi tam çıktıyı korur). Tercihe bağlı. |
| `compact_keep_last_n_turns` | int | `4` | En son N turu asla sıkıştırma. |
| `compact_min_chars` | int | `800` | Yalnızca bundan büyük bir sonucu sıkıştır. |
| `compact_trigger_chars` | int | `16000` | Bu kadar eski yığın biriktiğinde bir sıkıştırma geçişi çalıştır. |

## `memory`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Vektör belleğini etkinleştirir. |
| `embedding_provider` | str | `"ollama"` | Gömme (embedding) sağlayıcısı (ollama, openai). |
| `embedding_model` | str | `"nomic-embed-text"` | Gömme modeli adı. |
| `embedding_host` | str | `"http://localhost:11434"` | `ollama` sağlayıcısı için gömme uç noktası (sohbet modeli host'undan bağımsız). |
| `embedding_api_key` | str | `""` | Gömme sağlayıcısı için API anahtarı. |
| `db_path` | str | `"~/.aethon/memory.sqlite"` | Vektör deposu için SQLite yolu. |
| `auto_recall` | bool | `false` | Her gelen mesajı gömer ve en iyi eşleşen bellekleri bir `## Recalled Memories` istem katmanı olarak enjekte eder (tercihe bağlı). |
| `recall_top_k` | int | `3` | Anımsanacak bellek sayısı. |
| `recall_min_score` | float | `0.0` | Yalnızca bu benzerlik düzeyinde veya üzerindeki eşleşmeleri enjekte et. |
| `recall_max_chars` | int | `1500` | Enjekte edilen anımsanan belleğin maksimum karakter sayısı. |

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

## `logging`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Kök günlükleyiciye (root logger) dönen bir dosya işleyicisi ekler (üçüncü taraf hatalarını da yakalar). |
| `level` | str | `"INFO"` | AETHON'un kendi günlükleyicileri için günlük düzeyi. |
| `third_party_level` | str | `"WARNING"` | Kütüphaneler için günlük düzeyi (strands/uvicorn/aiogram/discord/slack). |

## `approval`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Kesinti tabanlı onay hook'unu etkinleştirir. |
| `requires_approval` | list[str] | `["shell", "file_write", "manage_tools", "manage_specialists"]` | Bu hook üzerinden onay gerektiren eylem türleri. |
| `timeout_seconds` | float | `120.0` | Reddetmeden önce bir insan onay yanıtı için beklenecek saniye. |

## `reliability`

Tüm kapılar **varsayılan olarak tavsiye niteliğindedir** (geri bildirim eklerler); `strict` onları sıkı kapılara çevirir.

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `strict` | bool | `false` | Bulguları tavsiye niteliğindeki geri bildirimden sıkı kapılara yükseltir. |
| `post_edit_verify` | bool | `true` | Düzenlenen dosyalarda bir doğrulama komutu çalıştırır ve bir `[Verify]` PASS/FAIL bloğu ekler. |
| `verify_cmd` | str | `""` | Doğrulama komutu; `{paths}`, düzenlenen yollarla değiştirilir. Boş = otomatik algıla (düzenlenen `*.py` üzerinde `ruff check`). |
| `verify_timeout` | int | `30` | Bir doğrulama çalıştırması terk edilmeden önceki saniye. |
| `completion_gate` | bool | `true` | Bir başarı iddiası doğrulama kanıtından yoksun olduğunda bir Tamamlanma Tanımı (Definition-of-Done) hatırlatıcısı ekler. |
| `anglicization_guard` | bool | `true` | Mevcut Türkçe metni yalnızca İngilizce metinle değiştiren düzenlemeleri duraklatır (tavsiye niteliğinde). |
| `input_validator` | bool | `true` | Hatalı biçimli araç çağrılarını iptal eder (boş shell komutu, eksik dosya yolu). |

## `core_loop`

Otonom çekirdek döngü (iş alımı → plan → sınırlı yürütücü → iş kanıtı makbuzu). Aksi belirtilmedikçe her ayar **tercihe bağlı / varsayılan olarak kapalıdır**.

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `intake_enabled` | bool | `false` | Net bir iş birimini sınıflandırır ve sohbet olarak yanıtlamak yerine planlanmış bir proje olarak açar. |
| `intake_work_phrases` | list[str] | (TR/EN ifadeler) | İş kararını zorlayan ifadeler. |
| `intake_chat_phrases` | list[str] | (TR/EN ifadeler) | Sohbet kararını zorlayan ifadeler (beraberlikte sohbet kazanır). |
| `plan_approval` | bool | `false` | Yürütücü çalıştığında, yeni planlanmış bir projeyi yürütmeden önce kullanıcı onayı ister. |
| `executor_enabled` | bool | `false` | Sınırlı proje yürütücüsünü etkinleştirir. |
| `executor_max_iterations` | int | `20` | Proje çalıştırması başına görev turlarına sıkı üst sınır. |
| `executor_max_task_attempts` | int | `3` | İlerleme olmayan N turdan sonra bir görevi bırakır (kalıcı). |
| `executor_stop_on_budget` | bool | `true` | `budget` tavanı aşıldığında görevler arasında durur. |
| `pulse_enabled` | bool | `true` | Yürütme sırasında köken kanalına ilerleme nabızları gönderir. |
| `pulse_every_n_tasks` | int | `3` | Yeni tamamlanan her N görevde bir nabız gönderir. |
| `receipt_enabled` | bool | `true` | Bir çalıştırma bittiğinde bir iş kanıtı makbuzu teslim eder. |
| `capability_diet` | bool | `false` | Ağır/alana özgü araçları yalnızca oturum ihtiyaç duyduğunda yükler. |
| `dynamic_specialists` | bool | `false` | `manage_specialists`'i açığa çıkarır; ajanın özel uzmanlar tanımlayıp kalıcılaştırmasına izin verir. |
| `allow_powerful_specialists` | bool | `false` | Bir dinamik uzmanın güçlü bir araç tutmasına izin verir (`shell`/`python_repl`/`file_write`/`editor`/`http_request`). |

## `telemetry`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Telemetri hook'unu etkinleştirir. |
| `max_history` | int | `10000` | Saklanan maksimum telemetri olayı sayısı. |

## `budget`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `daily_usd` | float | `0.0` | USD cinsinden günlük harcama tavanı; `0` = sınırsız (yalnızca ölç). Turlar tavana yaklaşıldığında uyarılır ve tavan aşıldığında engellenir (ortam/zamanlayıcı turlarını da durdurur). |
| `warn_ratio` | float | `0.8` | Harcama, tavanın bu oranını aştığında uyarır. |
| `pricing` | dict | `{}` | Yerleşik fiyatlandırma tablosunu geçersiz kılar: 1M token başına USD, `{model_substring: {"input": x, "output": y}}`. |

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

## `repo_map`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `false` | Okunan dosyaların kompakt bir `path → {purpose, symbols, hash}` özetini `workspace/REPO_MAP.json` içinde önbelleğe alır ve bir `## Repo Map` istem katmanı enjekte eder (tercihe bağlı). |
| `max_files` | int | `100` | Haritayı en yeni N dosyayla sınırlar. |
| `max_file_bytes` | int | `200000` | Bundan büyük dosyaları atlar. |
| `max_snapshot_chars` | int | `2000` | İstem katmanı boyut üst sınırı. |

## `retention`

| Alan | Tür | Varsayılan | Anlam |
|---|---|---|---|
| `enabled` | bool | `true` | Açılışta oturum-sıfırlama yedeklerini + kayıtları budar (`aethon doctor` disk kullanımını raporlar). |
| `cleared_keep` | int | `10` | Oturum başına saklanan en yeni `cleared/batch_*` sayısı (`0` = sınırsız). |
| `recordings_keep` | int | `20` | Saklanan en yeni kayıt arşivleri. |
| `recordings_max_age_days` | int | `0` | Kayıtlarda yaş üst sınırı; `0` = yaş sınırı yok. |

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
`ambient` ve `prompt` blokları için bkz. **[Yapılandırma](../getting-started/configuration.md)** (Yetenekler ve çalışma zamanı özellikleri bölümü)
ve **[Yetenekler](../concepts/capabilities.md)**.
