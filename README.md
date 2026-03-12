# AETHON

**Kisisel AI Asistan** — Yerel LLM, cok kanal, cok agent, tam kontrol.

> *Autonomous Execution Through Harmonized Orchestrated Networks*

```
Python 3.10+  |  Strands Agents SDK  |  Ollama  |  294 Test  |  v0.1.0
```

---

## AETHON Nedir?

AETHON, yerel makinenizde calisan, cok kanalli, cok agentli bir kisisel AI asistandir.

- **Yerel ve ozel** — Tum veriler ve model calismalari makinenizde kalir. Bulut bagimliligi yok.
- **6 kanal** — CLI, WebChat, Telegram, Discord, Slack ve WhatsApp uzerinden erisim.
- **Uzman takim** — Tek bir agent degil; Kodcu, Arastirmaci, Analist ve Planlayici uzmanlardan olusan bir takim.
- **SOP sistemi** — Tekrarlayan is akislarini yapilandirilmis prosedurlerle otomatiklestirin.
- **Zamanlayici** — Cron tabanli gorev zamanlama ile SOP'lari otomatik calistirin.
- **Guvenlik oncelikli** — 7 katmanli guvenlik mimarisi, hafiza korumasi, komut filtreleme.

```
┌─────────────────────────────────────────────────────────────┐
│                        KANALLAR                             │
│  CLI  │  WebChat  │  Telegram  │  Discord  │  Slack  │  WA │
└───────────────────────────┬─────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  MESSAGE ROUTER │
                   │  + Auth + Queue │
                   └────────┬────────┘
                            │
              ┌─────────────▼─────────────┐
              │      AETHON RUNTIME       │
              │                           │
              │   ┌─────────────────────┐ │
              │   │   ORCHESTRATOR      │ │
              │   │   (Strands Agent)   │ │
              │   └──┬──────┬───────┬───┘ │
              │      │      │       │     │
              │   Kodcu  Arastir  Analist │
              │   Agent  maci    Agent    │
              │          Agent            │
              └─────────────┬─────────────┘
                            │
              ┌─────────────▼─────────────┐
              │       ALTYAPI             │
              │  Hafiza │ Session │ Config │
              │  SQLite │ JSON    │ YAML   │
              └───────────────────────────┘
```

---

## Ozellikler

### Cok Kanalli Erisim

| Kanal | Teknoloji | Aciklama |
|-------|-----------|----------|
| CLI | prompt_toolkit + rich | Terminal arayuzu |
| WebChat | FastAPI + WebSocket | Tarayici tabanli sohbet |
| Telegram | aiogram 3.x | Bot API polling |
| Discord | discord.py 2.x | Gateway WebSocket |
| Slack | slack-bolt | Socket Mode |
| WhatsApp | neonize | QR eslestirme |

### Uzman Agent Takimi

| Agent | Gorev | Tool'lar |
|-------|-------|---------|
| Orchestrator | Yonlendirme, basit gorevler | Tum tool'lar + delegasyon |
| Kodcu | Kod yazma, debug, refactoring | shell, editor, file_read/write |
| Arastirmaci | Bilgi toplama, analiz | http_request, file_read |
| Analist | Veri analizi, raporlama | python_repl, calculator |
| Planlayici | Proje planlama, gorev dagilimi | think, file_read |

### SOP Is Akislari

Dahili SOP'lar:

| SOP | Komut | Aciklama |
|-----|-------|----------|
| Code Assist | `/code-assist` | Kod yazma, duzeltme, refactoring |
| PDD | `/pdd` | Puzzle-Driven Development |
| Morning Brief | `/morning-brief` | Sabah brifing raporu |

Ozel SOP'larinizi `~/.aethon/workspace/sops/` dizinine ekleyebilirsiniz.

### Hafiza Sistemi

```
Uzun Vadeli Hafiza ─── SQLite + Ollama Embeddings (semantik arama)
Session Hafiza     ─── FileSessionManager (konusma gecmisi)
Calisma Hafiza     ─── SummarizingConversationManager (context window)
```

### Dashboard ve API

- **Web Dashboard** — Oturumlar, hafiza, telemetri, zamanlanmis gorevler
- **REST API** — `/api/sessions`, `/api/memory`, `/api/telemetry`, `/api/config`
- **WebSocket** — `/ws/chat` (sohbet), `/ws/telemetry` (canli metrikler)
- **Webhook** — `/webhook/{channel}`, `/webhook/trigger` (HMAC-SHA256)

### Zamanlayici

APScheduler ile cron-tabanli gorev zamanlama:

```yaml
scheduler:
  jobs:
    morning-brief:
      cron: "0 9 * * 1-5"    # Hafta ici sabah 9
      sop_name: morning-brief
      channel: telegram
```

### Guvenlik

7 katmanli guvenlik mimarisi:

1. **Ag** — Tum servisler `127.0.0.1`, `0.0.0.0` kullanilmaz
2. **Kimlik** — Kanal bazli kullanici dogrulama (`allowed_senders`)
3. **Tool** — Tehlikeli komut filtreleme (`blocked_commands`)
4. **Dosya** — Workspace sinirlamasi
5. **Hafiza** — MemoryGuard (API key, sifre, token, SSH, kredi karti engelleme)
6. **Icerik** — SummarizingConversationManager ile veri sinirlamasi
7. **Onay** — Tehlikeli tool'lar icin kullanici onayi

---

## Gereksinimler

| Gereksinim | Minimum | Tavsiye |
|------------|---------|---------|
| Python | 3.10+ | 3.12+ |
| RAM | 16 GB | 32 GB+ |
| Disk | 50 GB (model icin) | SSD |
| OS | macOS (Apple Silicon) | macOS 14+ |
| Ollama | En son surum | — |

---

## Kurulum

### 1. Ollama Kurulumu

```bash
brew install ollama
ollama serve
```

### 2. Model Indirme

```bash
ollama pull qwen3-coder-next      # Ana model (80B MoE)
ollama pull nomic-embed-text       # Embedding modeli
```

### 3. AETHON Kurulumu

```bash
git clone <repo-url> aethon
cd aethon
pip install -e ".[all]"
```

Sadece belirli ozellikler icin:

```bash
pip install -e "."                  # Sadece cekirdek (CLI + WebChat)
pip install -e ".[channels]"        # + Telegram, Discord, Slack
pip install -e ".[memory]"          # + Vektor hafiza
pip install -e ".[scheduler]"       # + Zamanlayici
pip install -e ".[mcp]"             # + MCP sunucu entegrasyonu
```

### 4. Yapilandirma (Opsiyonel)

Ilk calistirmada `~/.aethon/` otomatik olusturulur. Ozellestirmek icin:

```bash
mkdir -p ~/.aethon
cat > ~/.aethon/config.yaml << 'EOF'
model:
  provider: ollama
  model_id: qwen3-coder-next
  host: http://localhost:11434

memory:
  enabled: true
  embedding_model: nomic-embed-text

channels:
  cli:
    enabled: true
  webchat:
    enabled: true
    port: 8080
EOF
```

---

## Baslangic

### Baslatma

```bash
python -m aethon start
```

veya:

```bash
aethon start
```

Cikti:

```
AETHON baslatiliyor...

  Provider: ollama
  Model: qwen3-coder-next
  WebChat: http://127.0.0.1:8080
  Memory: nomic-embed-text (aktif)
  Multi-Agent: aktif
  SOP'lar: 5 adet
  Zamanlayici: aktif
  Telemetri: aktif
  Dashboard: http://127.0.0.1:8080/dashboard
  Kanallar: CLI, WebChat

AETHON>
```

### CLI Kullanimi

```
AETHON> Merhaba, bugun ne yapacagiz?
AETHON> Bu Python dosyasindaki hatalari bul ve duzelt
AETHON> /code-assist Yeni bir REST API endpoint yaz
AETHON> Sabah 9'da brifing zamanla
```

### WebChat

Tarayicinizda `http://127.0.0.1:8080/ui` adresini acin.

### Dashboard

`http://127.0.0.1:8080/dashboard` — Oturumlar, hafiza, telemetri, zamanlanmis gorevler.

### Webhook

```bash
# SOP tetikleme
curl -X POST http://127.0.0.1:8080/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"sop_name": "morning-brief", "channel": "telegram"}'

# Duz mesaj
curl -X POST http://127.0.0.1:8080/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"text": "Proje durumu nedir?"}'
```

---

## Workspace Dosyalari

AETHON'un davranisini 3 dosya ile kontrol edin:

| Dosya | Konum | Aciklama |
|-------|-------|----------|
| `SOUL.md` | `~/.aethon/workspace/SOUL.md` | Agent kisiligi ve davranis kurallari |
| `TOOLS.md` | `~/.aethon/workspace/TOOLS.md` | Kullanici tercihleri ve konvansiyonlar |
| `CONTEXT.md` | `~/.aethon/workspace/CONTEXT.md` | Mevcut baglam (otomatik guncellenir) |

**SOUL.md Ornegi:**
```markdown
# AETHON — Kisilik

Sen AETHON, Mert'in kisisel AI asistanisin.
Mac uzerinde Ollama ile calisiyorsun.

## Davranis
- Turkce ve Ingilizce konusabilirsin.
- Kisa ve oz yanit ver.
- Hata yaptiginda kabul et ve duzelt.
```

---

## Kanal Yapilandirmasi

### Telegram

```yaml
channels:
  telegram:
    enabled: true
    token: "${TELEGRAM_BOT_TOKEN}"

security:
  allowed_senders:
    telegram: ["12345678"]
```

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
```

### Discord

```yaml
channels:
  discord:
    enabled: true
    token: "${DISCORD_BOT_TOKEN}"
```

### Slack

```yaml
channels:
  slack:
    enabled: true
    bot_token: "${SLACK_BOT_TOKEN}"
    app_token: "${SLACK_APP_TOKEN}"
```

---

## Dizin Yapisi

```
~/.aethon/                       # Kullanici veri dizini
  ├── config.yaml                # Yapilandirma
  ├── workspace/                 # Agent calisma alani
  │   ├── SOUL.md                # Kisilik
  │   ├── TOOLS.md               # Tercihler
  │   ├── CONTEXT.md             # Baglam
  │   └── sops/                  # Ozel SOP dosyalari
  ├── sessions/                  # Konusma gecmisleri
  ├── memory.sqlite              # Uzun vadeli hafiza
  ├── logs/                      # Log dosyalari
  └── credentials/               # Token'lar

aethon/                          # Proje kaynak kodu
  ├── pyproject.toml
  ├── aethon/
  │   ├── config.py              # AethonConfig (17 Pydantic model)
  │   ├── gateway/               # Gateway + Router + Webhooks
  │   ├── channels/              # 6 kanal adapteri
  │   ├── agent/                 # Runtime + Hooks + Specialists
  │   ├── tools/                 # Tool'lar (delegate, memory, context, scheduler, MCP)
  │   ├── memory/                # VectorMemory (SQLite + Ollama embeddings)
  │   ├── sops/                  # SOPRunner + dahili SOP'lar
  │   └── ui/                    # Web dashboard
  └── tests/                     # 294 test
```

---

## Gelistirme

### Test Calistirma

```bash
# Tum testler
pytest tests/ -v

# Belirli modul
pytest tests/test_config.py -v

# Entegrasyon testleri (Ollama gerektirir)
pytest tests/test_integration.py -v
```

### Test Durumu

| Faz | Test Sayisi | Durum |
|-----|-------------|-------|
| Faz 1 — Cekirdek | 64 | Gecen |
| Faz 2 — Kanallar + Hafiza | 120 | Gecen |
| Faz 3 — Multi-Agent + SOP | 178 | Gecen |
| Faz 4 — Cilalama | 294 | Gecen |

### Bagimlilklar

```
strands-agents         — Agent framework (cekirdek)
strands-agents-tools   — 47+ tool
fastapi + uvicorn      — WebChat + Dashboard + Webhook + API
aiogram                — Telegram
discord.py             — Discord
slack-bolt             — Slack
apscheduler            — Zamanlayici
pyyaml + pydantic      — Config
mcp (opsiyonel)        — MCP sunucu entegrasyonu
```

---

## Dokumantasyon

Detayli dokumantasyon `docs/` dizininde:

| Dokuman | Aciklama |
|---------|----------|
| [Urun Tanimi](docs/product/PRODUCT.md) | Ozellikler, mimari bakis |
| [Baslangic Rehberi](docs/product/GETTING-STARTED.md) | Kurulum ve hizli baslangic |
| [Config Referansi](docs/product/CONFIGURATION.md) | Tum ayarlar |
| [API Referansi](docs/product/API-REFERENCE.md) | HTTP, WebSocket, webhook, tool'lar |
| [Mimari](docs/product/ARCHITECTURE.md) | Teknik mimari ve veri akislari |
| [Guvenlik](docs/development/SECURITY.md) | Guvenlik modeli ve tehdit analizi |
| [Yol Haritasi](docs/development/ROADMAP.md) | Proje gelistirme adimlari |

---

## Teknoloji

| Katman | Teknoloji |
|--------|-----------|
| Agent Framework | [Strands Agents SDK](https://github.com/strands-agents/sdk-python) |
| LLM | [Qwen3-Coder-Next](https://ollama.com/) via Ollama |
| Embedding | nomic-embed-text via Ollama |
| Gateway | FastAPI + Uvicorn |
| CLI | prompt_toolkit + rich + click |
| Veritabani | SQLite (hafiza), JSON (session) |
| Zamanlayici | APScheduler |
| Config | PyYAML + Pydantic v2 |

---

## Lisans

MIT
