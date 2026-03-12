# AETHON — Urun Dokumani

> **AETHON** — Autonomous Execution Through Harmonized Orchestrated Networks
> Versiyon: 0.1.0 | Tarih: 2026-03-12

---

## 1. Urun Ozeti

AETHON, **kendi makinende calisan, tum mesajlasma kanallarindan erisilebilen, coklu-agent takimi tarafindan desteklenen kisisel bir AI asistan sistemidir.**

- **Tek kullanici** icin tasarlanmis — senin kisisel AI asistanin
- **Lokal calisir** — Mac uzerinde Ollama ile, bulut bagimliligi yok
- **Her yerden erisim** — WhatsApp, Telegram, Discord, Slack, WebChat, CLI
- **Akilli takim** — tek agent degil, uzman agent takimi
- **Yapilandirilmis is akislari** — SOP'lar ile tekrarlanabilir gorevler

---

## 2. Vizyon

### 2.1 Problem

Mevcut AI asistan sistemleri (OpenClaw, vb.) su sorunlara sahip:

1. **Tek agent sinirlamasi** — Her seyi tek bir agent yapmaya calisiyor
2. **Guvenlik aciklari** — CVE-2026-25253, 824+ zararli skill, WebSocket hijack
3. **Is akisi eksikligi** — Agent kendi basina karar veriyor, yapilandirilmis akis yok
4. **Cikti dogrulamasi yok** — Agent ne uretirse o kabul ediliyor
5. **Node.js ekosistemi** — ML/AI kutuphaneleri ile dogal uyumsuzluk

### 2.2 Cozum

AETHON bu sorunlarin hepsini cozer:

| Problem | AETHON Cozumu |
|---------|---------------|
| Tek agent | Coklu uzman agent takimi (Swarm + Graph + Agent-as-Tool) |
| Guvenlik aciklari | Loopback-only, marketplace yok, hook-tabanli policy |
| Is akisi eksikligi | SOP-gudumlu yapilandirilmis akislar |
| Cikti dogrulamasi | Pydantic ile zorunlu yapilandirilmis cikti |
| Node.js | Python 3.10+ — ML/AI ekosistemi ile dogal uyum |

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
| WebChat | `FastAPI` + `websockets` | HTTP/WS localhost:18790 |
| Telegram | `aiogram` 3.x | Bot Token (BotFather) |
| Discord | `discord.py` 2.x | Bot Token (Developer Portal) |
| Slack | `slack-bolt` | Bot Token + App Token (Socket Mode) |
| WhatsApp | `neonize` / bridge | QR kod eslestirme |

Tum kanallar **ayni agent runtime**'a baglanir. Hangi kanaldan yazarsan yaz, ayni AETHON sana yanit verir.

### 3.2 Multi-Agent Takim

OpenClaw tek bir agent (Pi) ile calisir. AETHON'da bir gorev geldiginde uzman bir takim devreye girer:

| Agent | Uzmanlık | Kullandigi Tool'lar |
|-------|----------|---------------------|
| **Orchestrator** | Ana yonlendirici, gorev delegasyonu | Tum delegate tool'lar |
| **Kodcu** | Kod yazma, test, debug, refactoring | `editor`, `shell`, `python_repl`, `file_write` |
| **Arastirmaci** | Web arastirmasi, dokumantasyon okuma | `http_request`, `file_read`, `think` |
| **Analist** | Veri analizi, grafik, rapor | `python_repl`, `calculator`, `file_write` |
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

### 3.4 Yapilandirilmis Cikti

Agent'in ciktisi Pydantic modeli ile dogrulanir:

```python
class MeetingNote(BaseModel):
    title: str
    attendees: list[str]
    action_items: list[ActionItem]
    next_meeting: datetime
```

Model bu formata uymak zorunda — hata varsa SDK otomatik olarak yeniden dener.

### 3.5 Guvenlik-Oncelikli Tasarim

| Katman | Koruma |
|--------|--------|
| Ag | Gateway sadece 127.0.0.1 — dis erisim imkansiz |
| Tool | BeforeToolCallEvent hook'u ile tehlikeli islemler engellenir |
| Dosya | Workspace-only erisim — diger dizinlere erisim engellenir |
| Hafiza | Yazma oncesi hassas bilgi tespiti |
| Icerik | Dis kaynaklardan gelen icerik filtreleme |
| Onay | Tehlikeli tool'lar icin Interrupt ile kullanici onayi |

### 3.6 Hafiza Sistemi

| Katman | Teknoloji | Omur |
|--------|-----------|------|
| Calisma Hafizasi | SummarizingConversationManager | Her model cagrisi |
| Session Hafizasi | FileSessionManager | Session boyunca |
| Uzun Vadeli Hafiza | SQLite + Ollama Embeddings | Aylar/yillar |

---

## 4. Teknoloji Yigini

### 4.1 Cekirdek

| Bilesken | Teknoloji |
|----------|-----------|
| **Dil** | Python 3.10+ |
| **Agent Framework** | Strands Agents SDK |
| **LLM** | Qwen3-Coder-Next (Ollama uzerinden) |
| **Model Provider** | OllamaModel (Strands SDK dahili) |
| **Multi-Agent** | Strands Swarm + GraphBuilder |
| **SOP** | strands-agents-sops |
| **Tool Ekosistemi** | strands-agents-tools (47+ tool) |

### 4.2 Altyapi

| Bilesken | Teknoloji |
|----------|-----------|
| **Async Runtime** | Python asyncio |
| **Web Framework** | FastAPI + Uvicorn |
| **WebSocket** | websockets / FastAPI WS |
| **CLI** | prompt_toolkit + rich + click |
| **Config** | PyYAML + Pydantic |
| **Veritabani** | SQLite (aiosqlite) |
| **Zamanlayici** | APScheduler |
| **Gozlemlenebilirlik** | OpenTelemetry (Strands dahili) |

### 4.3 Kanal Kutuphaneleri

| Kanal | Kutuphane | Versiyon |
|-------|-----------|---------|
| Telegram | aiogram | 3.x |
| Discord | discord.py | 2.x |
| Slack | slack-bolt | 1.18+ |
| WhatsApp | neonize / whatsapp-web.js bridge | - |

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

**Strands Entegrasyonu:**
```python
from strands.models import OllamaModel

model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3-coder-next",
    temperature=1.0,
    top_p=0.95,
    options={"top_k": 40}
)
```

---

## 6. OpenClaw ile Karsilastirma

| Ozellik | OpenClaw | AETHON |
|---------|----------|--------|
| **Runtime** | Node.js 22+ | Python 3.10+ |
| **Agent** | Pi (4 tool) | Strands Agent (47+ tool) |
| **Multi-Agent** | YOK | Swarm + Graph + Agent-as-Tool |
| **SOP/Workflow** | YOK | 5 dahili + ozel SOP yazma |
| **Structured Output** | YOK | Pydantic dogrulama |
| **Tool Tanimlama** | SKILL.md (markdown) | @tool (Python — tip guvenligi) |
| **Kanallar** | 22+ | 6 (moduler, genisletilebilir) |
| **Guvenlik** | CVE'ler, zararli skill'ler | Tasarimdan guvenli |
| **Gozlemlenebilirlik** | Sinirli | OpenTelemetry dahili |
| **Ses** | ElevenLabs TTS/STT | Bidi Streaming (deneysel) |
| **Human-in-the-Loop** | Sinirli | Interrupt mekanizmasi |
| **Model Provider** | Coklu (Pi-tabanli) | 11+ provider |

---

## 7. Kullanim Senaryolari

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

### Senaryo 3: Sabah Brifing
```
Cron (09:00): /morning-brief SOP tetiklenir
AETHON:
  → SOP adimlari sirayla calisir
  → Takvim, gorevler, haberler kontrol edilir
  → Brifing formatlanir ve Telegram'dan gonderilir
```

### Senaryo 4: Proje Planlama
```
Kullanici (CLI): "/pdd yeni e-ticaret backend"
AETHON:
  → PDD SOP calisir
  → Planlayici: Gereksinimleri toplar
  → Kodcu: Teknik tasarim dokumani olusturur
  → Sonuc workspace'e kaydedilir
```

---

## 8. Proje Sinirlamalari

### 8.1 Bilinli Kisitlamalar
- **Tek kullanici** — Coklu kullanici destegi yok (gerekmiyor)
- **Lokal calisma** — Bulut deploy yok (guvenlik icin)
- **6 kanal** — OpenClaw'un 22 kanali yok ama en onemli 6'si var
- **Ollama bagimli** — Model degisikligi icin Ollama gerekli

### 8.2 Model Sinirlamalari
- Qwen3-Coder-Next **sadece non-thinking** modunda calisir
- 80B model — Mac'te RAM kullanimi yuksek olabilir
- Tool calling guvenilirligi Ollama native API'ye bagimli

### 8.3 Bilinen Riskler
- WhatsApp adaptoru (neonize) kararlilik sorunu yasayabilir
- Ollama embedding API performansi buyuk veri setlerinde sinirli
- Multi-agent Swarm modunda token tuketimi yuksek olabilir

---

## 9. Basari Kriterleri

### MVP (Faz 1 Sonu)
- [ ] CLI'dan AETHON ile konusabilme
- [ ] WebChat'ten AETHON ile konusabilme
- [ ] Ollama + Qwen3-Coder-Next calisiyor
- [ ] Temel tool'lar calisiyor (file_read, file_write, shell, editor)
- [ ] Session yonetimi calisiyor (konusma gecmisi korunuyor)
- [ ] Guvenlik hook'lari aktif

### Tam Urun (Faz 4 Sonu)
- [ ] Tum 6 kanal calisiyor
- [ ] Multi-agent takim calisiyor
- [ ] SOP'lar calisiyor
- [ ] Uzun vadeli hafiza calisiyor
- [ ] Zamanlayici calisiyor
- [ ] Dashboard calisiyor
- [ ] Performans kabul edilebilir seviyede

---

## 10. Sozluk

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
