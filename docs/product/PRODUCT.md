# AETHON — Urun Dokumani

> **AETHON** — Autonomous Execution Through Harmonized Orchestrated Networks
> Versiyon: 1.0.0 | Tarih: 2026-03-12

---

## 1. Urun Ozeti

AETHON, **kendi makinende calisan, tum mesajlasma kanallarindan erisilebilen, coklu-agent takimi tarafindan desteklenen kisisel bir AI asistan sistemidir.**

- **Tek kullanici** icin tasarlanmis — senin kisisel AI asistanin
- **Lokal calisir** — Mac uzerinde Ollama ile, bulut bagimliligi yok
- **Her yerden erisim** — WhatsApp, Telegram, Discord, Slack, WebChat, CLI
- **Akilli takim** — tek agent degil, uzman agent takimi
- **Yapilandirilmis is akislari** — SOP'lar ile tekrarlanabilir gorevler
- **Guvenlik-oncelikli** — 7 katmanli guvenlik mimarisi

---

## 2. Vizyon

### 2.1 Problem

Mevcut AI asistan sistemleri su sorunlara sahip:

1. **Tek agent sinirlamasi** — Her seyi tek bir agent yapmaya calisiyor
2. **Guvenlik zafiyetleri** — Dis erisime acik portlar, dogrulanmamis araclar
3. **Is akisi eksikligi** — Agent kendi basina karar veriyor, yapilandirilmis akis yok
4. **Cikti dogrulamasi yok** — Agent ne uretirse o kabul ediliyor
5. **Gozlemlenebilirlik yok** — Neler oldugundan haberdar olunmuyor

### 2.2 Cozum

| Problem | AETHON Cozumu |
|---------|---------------|
| Tek agent | Coklu uzman agent takimi (Swarm + Graph + Agent-as-Tool) |
| Guvenlik zafiyetleri | Loopback-only, marketplace yok, hook-tabanli policy |
| Is akisi eksikligi | SOP-gudumlu yapilandirilmis akislar |
| Cikti dogrulamasi | Pydantic ile zorunlu yapilandirilmis cikti |
| Gozlemlenebilirlik | Telemetri dashboard + canli metrik stream |

### 2.3 Hedef Kullanici

**Tek kullanici: Mert Ozbas**

- Backend gelistirici (Python, asyncio, WebSocket, OOP)
- AI/ML agent sistemleri ile calisiyor
- Mac uzerinde lokal gelistirme yapiyor
- Turkce ve Ingilizce konusuyor

---

## 3. Temel Ozellikler

### 3.1 Coklu Kanal Erisimi

| Kanal | Kutuphane | Baglanti |
|-------|-----------|----------|
| CLI | `prompt_toolkit` | Terminal stdin/stdout |
| WebChat | `FastAPI` + `websockets` | HTTP/WS localhost:8080 |
| Telegram | `aiogram` 3.x | Bot Token (BotFather) |
| Discord | `discord.py` 2.x | Bot Token (Developer Portal) |
| Slack | `slack-bolt` | Bot Token + App Token (Socket Mode) |
| WhatsApp | `neonize` / bridge | QR kod eslestirme |

Tum kanallar **ayni agent runtime**'a baglanir. Hangi kanaldan yazarsan yaz, ayni AETHON sana yanit verir.

### 3.2 Multi-Agent Takim

Bir gorev geldiginde uzman bir takim devreye girer:

| Agent | Uzmanlik | Kullandigi Tool'lar |
|-------|----------|---------------------|
| **Orchestrator** | Ana yonlendirici, gorev delegasyonu | Tum delegate tool'lar |
| **Kodcu** | Kod yazma, test, debug, refactoring | `editor`, `shell`, `file_write` |
| **Arastirmaci** | Web arastirmasi, dokumantasyon okuma | `http_request`, `file_read`, `think` |
| **Analist** | Veri analizi, grafik, rapor | `file_write`, `think` |
| **Planlayici** | Gorev bolme, onceliklendirme | `file_read`, `file_write`, `think` |

**3 Calisma Modu:**

1. **Agent-as-Tool** — Orchestrator, uzman agent'lari tool olarak cagirir (`ask_coder(task)`)
2. **Swarm** — Agent'lar birbirine gorev devreder (isbirligi)
3. **Graph** — Agent'lar belirli sirada calisir (pipeline: Planlama → Arastirma → Kodlama)

### 3.3 SOP Is Akislari

Tekrarlanan gorevler icin standart operasyon prosedurleri:

| SOP | Tetikleme | Aciklama |
|-----|-----------|----------|
| `code-assist` | `/code-assist` | TDD-tabanli kod implementasyonu (Explore→Plan→Code→Commit) |
| `pdd` | `/pdd` | Prompt-Driven Development — fikirden tasarim dokumanina |
| `codebase-summary` | `/codebase-summary` | Kapsamli codebase dokumantasyonu olustur |
| `morning-brief` | `/morning-brief` | Sabah brifing hazirla (ozel) |
| `weekly-report` | `/weekly-report` | Haftalik rapor hazirla (ozel) |

**Ozel SOP yazma destegi** — Kendi is akislarini markdown olarak tanimlayabilirsin.

### 3.4 Zamanlayici (Scheduler)

Cron tabanli otomatik SOP tetikleme:

```yaml
scheduler:
  enabled: true
  jobs:
    morning-brief:
      cron: "0 9 * * 1-5"     # Hafta ici sabah 9
      sop_name: "morning-brief"
      channel: "telegram"
```

Agent'a sozlu komut da verebilirsin: "Her gun sabah 9'da morning-brief calistir"

### 3.5 Webhook Destegi

Dis sistemlerden AETHON'u tetikleme:

```bash
# Kanal bazli
curl -X POST http://localhost:8080/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"text": "Merhaba"}'

# SOP tetikleyici
curl -X POST http://localhost:8080/webhook/trigger \
  -d '{"sop_name": "code-assist", "text": "login ekranini yap"}'
```

HMAC-SHA256 secret ile guvenli webhook dogrulamasi desteklenir.

### 3.6 Web Dashboard

Tarayicidan AETHON'u izle: `http://localhost:8080/dashboard`

- **Oturumlar** — Aktif session'lari gor
- **Hafiza** — Uzun vadeli hafiza iceriklerini ara
- **Telemetri** — Tool/Model cagri istatistikleri
- **Zamanlanmis Gorevler** — Cron job'lari gor
- **Canli Metrikler** — WebSocket ile gercek zamanli akis

### 3.7 MCP Entegrasyonu

Model Context Protocol ile dis araclari bagla:

```yaml
mcp:
  enabled: true
  servers:
    - command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
```

MCP sunucularinin tool'lari otomatik olarak agent'a eklenir.

### 3.8 Guvenlik-Oncelikli Tasarim

| Katman | Koruma |
|--------|--------|
| Ag | Gateway sadece 127.0.0.1 — dis erisim imkansiz |
| Kimlik | Allowlist-tabanli sender dogrulama |
| Tool | SecurityHookProvider ile tehlikeli islemler engellenir |
| Dosya | Workspace-only erisim — diger dizinlere erisim engellenir |
| Hafiza | MemoryGuardHook ile hassas bilgi tespiti (API key, password, token) |
| Icerik | Dis kaynaklardan gelen icerik filtreleme |
| Onay | ApprovalHookProvider ile Interrupt bazli kullanici onayi |

### 3.9 Hafiza Sistemi

| Katman | Teknoloji | Omur |
|--------|-----------|------|
| Calisma Hafizasi | SummarizingConversationManager | Her model cagrisi |
| Session Hafizasi | FileSessionManager | Session boyunca |
| Uzun Vadeli Hafiza | SQLite + Ollama Embeddings | Aylar/yillar |

Embedding LRU cache ile ayni text'ler icin tekrar API cagrisi yapmaz.

### 3.10 Telemetri ve Gozlemlenebilirlik

- **TelemetryHookProvider** — Her tool ve model cagrisini izler
- **Metrikler** — Cagri sayisi, ortalama sure, hata sayisi
- **WebSocket Stream** — Canli metrik akisi `/ws/telemetry`
- **Dashboard API** — `/api/telemetry` ile JSON erisi

### 3.11 CONTEXT.md Otomatik Guncelleme

Agent calismasi sirasinda mevcut baglami otomatik gunceller:

```
Kullanici: "Mevcut projem HashTrade v2"
AETHON: update_context("proje", "HashTrade v2") → CONTEXT.md guncellenir
```

---

## 4. Teknoloji Yigini

### 4.1 Cekirdek

| Bilesen | Teknoloji |
|---------|-----------|
| **Dil** | Python 3.10+ |
| **Agent Framework** | Strands Agents SDK |
| **LLM** | Qwen3-Coder-Next (Ollama uzerinden) |
| **Model Provider** | OllamaModel (Strands SDK dahili) |
| **Multi-Agent** | Strands Swarm + GraphBuilder |
| **Tool Ekosistemi** | strands-agents-tools (47+ tool) |

### 4.2 Altyapi

| Bilesen | Teknoloji |
|---------|-----------|
| **Async Runtime** | Python asyncio |
| **Web Framework** | FastAPI + Uvicorn |
| **WebSocket** | websockets / FastAPI WS |
| **CLI** | prompt_toolkit + rich + click |
| **Config** | PyYAML + Pydantic |
| **Veritabani** | SQLite |
| **Zamanlayici** | APScheduler |
| **Gozlemlenebilirlik** | TelemetryHookProvider + Dashboard |

---

## 5. Model: Qwen3-Coder-Next

| Ozellik | Deger |
|---------|-------|
| Parametreler | 80B toplam / 3B aktif (MoE) |
| Context | 256K token |
| Mimari | 48 katman, 512 uzman / 10 aktif |
| Mod | Non-thinking (SADECE) |
| Tool Calling | Evet (ChatML formati) |
| FIM | Evet (Fill-in-the-Middle) |
| Ollama | `ollama pull qwen3-coder-next` |

**Onerilen Sampling:**
- Temperature: 1.0
- Top-P: 0.95
- Top-K: 40

---

## 6. Kullanim Senaryolari

### Senaryo 1: Kod Gelistirme
```
Kullanici (Telegram): "login sayfasini implement et"
AETHON:
  → Planlayici: Gorevi adim adim boler
  → Kodcu: TDD ile implement eder (test → kod → refactor)
  → Kullaniciya sonuc bildirilir
```

### Senaryo 2: Arastirma
```
Kullanici (WhatsApp): "FastAPI vs Django karsilastirmasi yap"
AETHON:
  → Arastirmaci: Web'de arastirir, dokumantasyon okur
  → Analist: Verileri analiz eder, karsilastirma tablosu olusturur
  → Kullaniciya rapor gonderilir
```

### Senaryo 3: Otomatik Sabah Brifing
```
Cron (09:00): /morning-brief SOP tetiklenir
AETHON:
  → SOP adimlari sirayla calisir
  → Takvim, gorevler, haberler kontrol edilir
  → Brifing formatlanir ve Telegram'dan gonderilir
```

### Senaryo 4: Webhook ile Entegrasyon
```
CI/CD Pipeline: POST /webhook/trigger {"sop_name":"codebase-summary"}
AETHON:
  → codebase-summary SOP tetiklenir
  → Rapor olusturulur
  → Sonuc Slack'e gonderilir
```

---

## 7. Proje Sinirlamalari

### 7.1 Bilinli Kisitlamalar
- **Tek kullanici** — Coklu kullanici destegi yok (gerekmiyor)
- **Lokal calisma** — Bulut deploy yok (guvenlik icin)
- **6 kanal** — En onemli 6 mesajlasma kanali destekleniyor
- **Ollama bagimli** — Model degisikligi icin Ollama gerekli

### 7.2 Model Sinirlamalari
- Qwen3-Coder-Next **sadece non-thinking** modunda calisir
- 80B model — Mac'te RAM kullanimi yuksek olabilir
- Tool calling guvenilirligi Ollama native API'ye bagimli

---

## 8. Basari Kriterleri — TAMAMLANDI

### MVP (Faz 1) ✅
- [x] CLI'dan AETHON ile konusabilme
- [x] WebChat'ten AETHON ile konusabilme
- [x] Ollama + Qwen3-Coder-Next calisiyor
- [x] Temel tool'lar calisiyor (file_read, file_write, shell, editor)
- [x] Session yonetimi calisiyor (konusma gecmisi korunuyor)
- [x] Guvenlik hook'lari aktif

### Tam Urun (Faz 4) ✅
- [x] Tum 6 kanal destegi (CLI, WebChat, Telegram, Discord, Slack, WhatsApp)
- [x] Multi-agent takim calisiyor (Orchestrator, Kodcu, Arastirmaci, Analist, Planlayici)
- [x] SOP'lar calisiyor (3 dahili + ozel SOP destegi)
- [x] Uzun vadeli hafiza calisiyor (SQLite + Ollama Embeddings)
- [x] Zamanlayici calisiyor (APScheduler + cron)
- [x] Dashboard calisiyor (7 API + WebSocket + UI)
- [x] Webhook destegi calisiyor (HMAC-SHA256)
- [x] Telemetri calisiyor (TelemetryHookProvider + canli stream)
- [x] MemoryGuard calisiyor (hassas bilgi engelleme)
- [x] MCP entegrasyonu calisiyor (dis tool sunuculari)
- [x] Performans optimizasyonlari (LRU cache, embedding cache, model warm-up)
- [x] **294 test geciyor**

---

## 9. Sozluk

| Terim | Aciklama |
|-------|----------|
| **Agent** | LLM + System Prompt + Tools bilesimi |
| **Swarm** | Agent'larin isbirligi ile gorev tamamlamasi |
| **Graph** | Agent'larin belirli sirada calistirilmasi |
| **SOP** | Standard Operating Procedure — yapilandirilmis is akisi |
| **Hook** | Agent yasam dongusundeki olaylara baglanilan callback |
| **Interrupt** | Agent calismasini duraklatip kullanici onayi isteme |
| **Gateway** | Tum kanal adaptorlerini koordine eden ana surec |
| **Adapter** | Belirli bir mesajlasma platformu ile iletisim kurma modulu |
| **Workspace** | Agent'in calisma dizini (SOUL.md, TOOLS.md, SOP'lar) |
| **Orchestrator** | Gorevleri uygun uzman agent'lara yonlendiren ana agent |
| **MCP** | Model Context Protocol — dis araclari agent'a baglamak icin standart |
| **Webhook** | HTTP POST ile dis sistemlerden tetikleme noktasi |
| **Telemetri** | Agent performansini izleme ve olcme mekanizmasi |
| **MemoryGuard** | Hafizaya hassas bilgi yazilmasini engelleyen guvenlik katmani |
