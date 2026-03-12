# AETHON — Yapilandirma Referansi

> `~/.aethon/config.yaml` dosyasindaki tum ayarlarin aciklamasi.

---

## Tam Config Ornegi

```yaml
# === Model ===
model:
  provider: ollama                    # ollama | openai | anthropic | litellm
  model_id: qwen3-coder-next         # Ollama model adi
  host: http://localhost:11434        # Ollama sunucu adresi
  temperature: 1.0                    # Sampling sicakligi
  max_tokens: 16384                   # Maks cikti token sayisi

# === Hafiza ===
memory:
  enabled: true
  embedding_model: nomic-embed-text   # Ollama embedding modeli
  db_path: ~/.aethon/memory.sqlite    # SQLite veritabani yolu

# === Oturum ===
session:
  storage_dir: ~/.aethon/sessions     # Session dosyalari dizini
  summary_ratio: 0.2                  # Konusma ozet orani (0.0-1.0)
  preserve_recent_messages: 10        # Son N mesaj korunur

# === Kanallar ===
channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 8080
  telegram:
    enabled: false
    token: "${TELEGRAM_BOT_TOKEN}"    # Ortam degiskeni referansi
  discord:
    enabled: false
    token: "${DISCORD_BOT_TOKEN}"
  slack:
    enabled: false
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
  whatsapp:
    enabled: false

# === Guvenlik ===
security:
  blocked_commands:                   # Yasakli komutlar
    - "rm -rf /"
    - "sudo "
    - "mkfs"
  allowed_senders:                    # Kanal bazli izinli kullanicilar
    telegram: ["12345678"]
    discord: ["98765432"]

# === Onay Mekanizmasi ===
approval:
  enabled: false                      # Tehlikeli tool'lar icin onay iste
  requires_approval:                  # Onay gerektiren tool'lar
    - shell
    - file_write

# === Multi-Agent ===
multi_agent:
  enabled: true

# === SOP ===
sops:
  enabled: true
  builtin_sops_enabled: true          # Dahili SOP'lari yukle

# === Telemetri ===
telemetry:
  enabled: true
  max_history: 10000                  # Maks metrik gecmisi

# === Hafiza Koruma ===
memory_guard:
  enabled: true
  custom_patterns:                    # Ek hassas bilgi pattern'leri
    - "internal_secret=\\S+"

# === Zamanlayici ===
scheduler:
  enabled: true
  default_channel: telegram           # Sonuclarin gonderilecegi varsayilan kanal
  jobs:                               # On-tanimli zamanlanmis gorevler
    morning-brief:
      cron: "0 9 * * 1-5"            # Hafta ici sabah 9
      sop_name: morning-brief
      channel: telegram

# === Dashboard ===
dashboard:
  enabled: true

# === Webhook ===
webhook:
  enabled: true
  secret: ""                          # HMAC-SHA256 dogrulama anahtari (bos = yok)

# === MCP ===
mcp:
  enabled: false
  servers:
    - command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]

# === Performans ===
performance:
  model_warmup: true                  # Baslangiçta model isitma
  session_cache_size: 10              # Bellekte tutulan maks session sayisi
  embedding_cache_size: 100           # LRU embedding cache boyutu

# === Dizinler ===
paths:
  workspace: ~/.aethon/workspace
  sessions: ~/.aethon/sessions
  logs: ~/.aethon/logs
  memory_db: ~/.aethon/memory.sqlite
  credentials: ~/.aethon/credentials
```

---

## Config Detaylari

### Model

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `provider` | str | `ollama` | Model saglayici: ollama, openai, anthropic, litellm |
| `model_id` | str | `qwen3-coder-next` | Model adi |
| `host` | str | `http://localhost:11434` | Ollama sunucu adresi |
| `temperature` | float | `1.0` | Sampling sicakligi (0.0-2.0) |
| `max_tokens` | int | `16384` | Maks cikti token sayisi |

### Memory

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `enabled` | bool | `true` | Uzun vadeli hafiza aktif mi |
| `embedding_model` | str | `nomic-embed-text` | Embedding modeli |
| `db_path` | str | `~/.aethon/memory.sqlite` | SQLite veritabani yolu |

### Channels

Her kanal icin:

| Alan | Tip | Aciklama |
|------|-----|----------|
| `enabled` | bool | Kanal aktif mi |
| `token` | str | Bot token (ortam degiskeni destekler: `${VAR}`) |
| `port` | int | WebChat icin dinleme portu |

### Telemetry

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `enabled` | bool | `true` | Telemetri toplama aktif mi |
| `max_history` | int | `10000` | Bellekte tutulan maks metrik sayisi |

### Memory Guard

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `enabled` | bool | `true` | Hassas bilgi korumasi aktif mi |
| `custom_patterns` | list[str] | `[]` | Ek regex pattern'leri |

**Varsayilan engellenen pattern'ler:**
- API key'ler (`api_key=...`)
- Sifreler (`password=...`)
- Token'lar (`secret=...`, `token=...`)
- SSH anahtarlari (`ssh-rsa ...`)
- Private key bloklari (`-----BEGIN ... PRIVATE KEY-----`)
- Kredi karti numaralari
- SSN numaralari

### Scheduler

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `enabled` | bool | `true` | Zamanlayici aktif mi |
| `default_channel` | str | `telegram` | Varsayilan sonuc kanali |
| `jobs` | dict | `{}` | On-tanimli cron job'lar |

**Cron formati:** `dakika saat gun ay haftaGunu`

| Ornek | Anlami |
|-------|--------|
| `0 9 * * *` | Her gun saat 9:00 |
| `0 9 * * 1-5` | Hafta ici saat 9:00 |
| `30 18 * * 5` | Cuma 18:30 |
| `0 0 1 * *` | Her ayin 1'i gece yarisi |

### Performance

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `model_warmup` | bool | `true` | Baslangiçta model isitma (ilk istek gecikmesini azaltir) |
| `session_cache_size` | int | `10` | Bellekte tutulan maks session sayisi (LRU) |
| `embedding_cache_size` | int | `100` | Embedding LRU cache boyutu |

---

## Ortam Degiskeni Destegi

Config'de `${VAR_NAME}` seklinde ortam degiskeni referansi kullanilabilir:

```yaml
channels:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"
```

AETHON config yuklerken `${}` degerlerini otomatik cozer.

---

## Workspace Dosyalari

| Dosya | Konum | Amac |
|-------|-------|------|
| `SOUL.md` | `~/.aethon/workspace/SOUL.md` | Agent kisilik ve davranis kurallari |
| `TOOLS.md` | `~/.aethon/workspace/TOOLS.md` | Kullanici tercihleri |
| `CONTEXT.md` | `~/.aethon/workspace/CONTEXT.md` | Mevcut baglam (otomatik guncellenir) |
| `sops/` | `~/.aethon/workspace/sops/` | Ozel SOP dosyalari |
