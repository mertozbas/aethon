# AETHON — Yol Haritasi

> Versiyon: 0.1.0 | Tarih: 2026-03-12

---

## Genel Bakis

AETHON 4 fazda gelistirilecek. Her faz kendi basina calisan, test edilebilir bir urun uretir.

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  FAZ 1   │───▶│  FAZ 2   │───▶│  FAZ 3   │───▶│  FAZ 4   │
│ Cekirdek │    │ Kanallar │    │  Multi   │    │ Cilalama │
│          │    │ + Hafiza │    │  Agent   │    │          │
│ 1-2 Hafta│    │ 1-2 Hafta│    │ + SOP    │    │ Surekli  │
│          │    │          │    │ 1-2 Hafta│    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     ▼               ▼               ▼               ▼
  CLI + Web       6 Kanal        Takim +          Uretim
  calisiyor       calisiyor      SOP'lar          kalitesi
```

---

## Faz 1: Cekirdek Runtime (1-2 Hafta)

**Hedef:** CLI ve WebChat uzerinden AETHON ile konusabilir hale gelmek.

**Oncelik:** P0 (zorunlu)

### Ciktilar
- `aethon start` komutu ile sistem baslar
- CLI'dan mesaj gonder/al
- WebChat'ten mesaj gonder/al (localhost:18790)
- Ollama + Qwen3-Coder-Next ile tool calling calisiyor
- Session yonetimi calisiyor (konusma devam ediyor)
- Temel guvenlik hook'lari aktif

### Gorev Listesi

| # | Gorev | Dosya(lar) | Bagimlilik | Tahmini Sure |
|---|-------|-----------|------------|-------------|
| 1.1 | Proje iskeleti (pyproject.toml, paket yapisi) | `pyproject.toml`, `aethon/__init__.py` | - | 1 saat |
| 1.2 | AethonConfig (YAML yukleyici + Pydantic modeller) | `aethon/config.py` | - | 2 saat |
| 1.3 | Mesaj modelleri (InboundMessage, OutboundMessage, MediaAttachment) | `aethon/channels/base.py` | - | 1 saat |
| 1.4 | ChannelAdapter ABC | `aethon/channels/base.py` | 1.3 | 1 saat |
| 1.5 | OllamaModel entegrasyonu ve baglanti testi | `aethon/agent/runtime.py` | 1.2 | 2 saat |
| 1.6 | SystemPromptComposer (SOUL.md + TOOLS.md + zaman) | `aethon/agent/prompt.py` | 1.2 | 2 saat |
| 1.7 | AethonRuntime (agent olusturma + mesaj isleme) | `aethon/agent/runtime.py` | 1.5, 1.6 | 3 saat |
| 1.8 | SecurityHookProvider (workspace check + blocked cmds) | `aethon/agent/hooks/security.py` | 1.7 | 2 saat |
| 1.9 | MessageRouter (session resolver + dispatch) | `aethon/gateway/router.py` | 1.7 | 2 saat |
| 1.10 | CLIAdapter (prompt_toolkit + rich) | `aethon/channels/cli.py` | 1.4, 1.9 | 3 saat |
| 1.11 | WebChatAdapter (FastAPI + WebSocket) | `aethon/channels/webchat.py` | 1.4, 1.9 | 3 saat |
| 1.12 | AethonGateway (adapter orkestrasyon) | `aethon/gateway/server.py` | 1.10, 1.11 | 2 saat |
| 1.13 | CLI entry point (__main__.py + click) | `aethon/__main__.py` | 1.12 | 2 saat |
| 1.14 | Varsayilan workspace sablonu (SOUL.md, TOOLS.md) | `workspace/` | - | 1 saat |
| 1.15 | Entegrasyon testi (CLI → Agent → Yanit) | `tests/` | 1.13 | 2 saat |

**Toplam tahmini sure: ~27 saat**

### Bagimlilk Grafigi

```
1.1 ──▶ 1.2 ──▶ 1.5 ──▶ 1.7 ──▶ 1.8
              ──▶ 1.6 ──▶ 1.7
  1.3 ──▶ 1.4 ──▶ 1.10 ──▶ 1.12 ──▶ 1.13 ──▶ 1.15
                 ──▶ 1.11 ──▶ 1.12
         1.7 ──▶ 1.9 ──▶ 1.10
                      ──▶ 1.11
```

### Basari Kriterleri
- [ ] `aethon start` baslatinca hata vermiyor
- [ ] CLI'da "Merhaba" yazinca anlamli yanit geliyor
- [ ] WebChat'te (localhost:18790) konusma yapilabiliyor
- [ ] Agent file_read, shell tool'larini kullanabiliyor
- [ ] Workspace disi dosya erisimi engelleniyor
- [ ] Session devam ediyor (yeni mesajda gecmis korunuyor)

---

## Faz 2: Kanallar + Hafiza (1-2 Hafta)

**Hedef:** Tum mesajlasma kanallari calisiyor, kalici hafiza aktif.

**Oncelik:** P1 (onemli)

**Onkosul:** Faz 1 tamamlanmis

### Ciktilar
- Telegram, Discord, Slack, WhatsApp adapterleri calisiyor
- Kanal-arasi session izolasyonu
- Uzun vadeli vektor hafiza (SQLite + Ollama embeddings)
- SummarizingConversationManager ile context yonetimi
- Media destegi (gorsel, dosya)

### Gorev Listesi

| # | Gorev | Dosya(lar) | Bagimlilik | Tahmini Sure |
|---|-------|-----------|------------|-------------|
| 2.1 | TelegramAdapter (aiogram 3.x) | `aethon/channels/telegram.py` | Faz 1 | 4 saat |
| 2.2 | DiscordAdapter (discord.py 2.x) | `aethon/channels/discord_adapter.py` | Faz 1 | 4 saat |
| 2.3 | SlackAdapter (slack-bolt + Socket Mode) | `aethon/channels/slack_adapter.py` | Faz 1 | 4 saat |
| 2.4 | WhatsAppAdapter (neonize veya bridge) | `aethon/channels/whatsapp.py` | Faz 1 | 6 saat |
| 2.5 | Media destegi (gorsel, dosya indirme/gonderme) | `aethon/channels/base.py` + adapterler | 2.1-2.4 | 4 saat |
| 2.6 | MessageRouter gelistirme (coklu kanal session) | `aethon/gateway/router.py` | 2.1-2.4 | 3 saat |
| 2.7 | VectorMemory (SQLite + Ollama /api/embed) | `aethon/memory/vector.py` | Faz 1 | 4 saat |
| 2.8 | manage_memory tool | `aethon/tools/memory_tool.py` | 2.7 | 2 saat |
| 2.9 | SummarizingConversationManager entegrasyonu | `aethon/agent/runtime.py` | Faz 1 | 2 saat |
| 2.10 | AethonSessionManager (kanal-bagli session) | `aethon/session/manager.py` | 2.6 | 3 saat |
| 2.11 | Gateway'e yeni adapterler ekle | `aethon/gateway/server.py` | 2.1-2.4, 2.6 | 2 saat |
| 2.12 | Kanal baglanti testleri | `tests/` | 2.11 | 3 saat |

**Toplam tahmini sure: ~41 saat**

### Basari Kriterleri
- [ ] Telegram'dan AETHON ile konusma yapilabiliyor
- [ ] Discord'dan AETHON ile konusma yapilabiliyor
- [ ] Slack'ten AETHON ile konusma yapilabiliyor
- [ ] WhatsApp'tan AETHON ile konusma yapilabiliyor (QR eslestirme sonrasi)
- [ ] Farkli kanallardan gelen mesajlar izole session'larda
- [ ] "Bunu hatirla: ..." dedikten sonra uzun vadeli hafizadan geri cagirilabiliyor
- [ ] Uzun konusmalarda context yonetimi calisiyor (ozet + son mesajlar)

---

## Faz 3: Multi-Agent + SOP (1-2 Hafta)

**Hedef:** Uzman agent takimi ve yapilandirilmis is akislari calisiyor.

**Oncelik:** P1 (onemli)

**Onkosul:** Faz 1 tamamlanmis (Faz 2 istege bagli)

### Ciktilar
- Kodcu, Arastirmaci, Analist, Planlayici agent'lar
- Agent-as-Tool delegasyonu
- Swarm ve Graph modlari
- SOP yukleme ve calistirma
- Dahili SOP'lar (code-assist, PDD)
- Ozel SOP yazma destegi
- Yapilandirilmis cikti (Pydantic)
- Interrupt mekanizmasi (kullanici onayi)

### Gorev Listesi

| # | Gorev | Dosya(lar) | Bagimlilik | Tahmini Sure |
|---|-------|-----------|------------|-------------|
| 3.1 | SpecialistFactory (Kodcu, Arastirmaci, Analist, Planlayici) | `aethon/agent/specialists.py` | Faz 1 | 4 saat |
| 3.2 | Delegate tool'lari (ask_coder, ask_researcher, ask_analyst) | `aethon/tools/delegate.py` | 3.1 | 3 saat |
| 3.3 | Orchestrator agent (delegate tool'larli ana agent) | `aethon/agent/runtime.py` | 3.2 | 3 saat |
| 3.4 | TeamOrchestrator — Swarm modu | `aethon/agent/teams.py` | 3.1 | 4 saat |
| 3.5 | TeamOrchestrator — Graph modu | `aethon/agent/teams.py` | 3.1 | 4 saat |
| 3.6 | SOPRunner (SOP yukleme + agent'a enjekte etme) | `aethon/sops/runner.py` | Faz 1 | 4 saat |
| 3.7 | Dahili SOP entegrasyonu (code-assist, PDD) | `aethon/sops/runner.py` | 3.6 | 2 saat |
| 3.8 | Ozel SOP yazma/yukleme | `aethon/sops/runner.py` | 3.6 | 2 saat |
| 3.9 | SOP tetikleme (/komut deseni) | `aethon/agent/runtime.py` | 3.6 | 2 saat |
| 3.10 | Yapilandirilmis cikti (Pydantic structured_output_model) | `aethon/agent/runtime.py` | Faz 1 | 2 saat |
| 3.11 | ApprovalHookProvider (Interrupt mekanizmasi) | `aethon/agent/hooks/approval.py` | Faz 1 | 3 saat |
| 3.12 | Multi-agent entegrasyon testleri | `tests/` | 3.3, 3.4, 3.5 | 3 saat |
| 3.13 | SOP entegrasyon testleri | `tests/` | 3.7 | 2 saat |

**Toplam tahmini sure: ~38 saat**

### Basari Kriterleri
- [ ] "Bu kodu implement et" diyen mesaj kodcu agent'a yonlendiriliyor
- [ ] Swarm modunda agent'lar birbirine gorev devrediyor
- [ ] Graph modunda pipeline sirayla calisiyor (Plan → Research → Code)
- [ ] `/code-assist` komutu ile SOP tetikleniyor
- [ ] Ozel SOP dosyasi yazilip yuklenebiliyor
- [ ] Tehlikeli tool cagrisi Interrupt ile duraklatiyor
- [ ] Yapilandirilmis cikti Pydantic modeli ile dogrulaniyor

---

## Faz 4: Cilalama + Ileri Ozellikler (Surekli)

**Hedef:** Uretim kalitesi, performans optimizasyonu, ileri ozellikler.

**Oncelik:** P2 (guzellestirme)

**Onkosul:** Faz 1-3 tamamlanmis

### Ciktilar
- Zamanlayici (cron-tabanli SOP tetikleme)
- Web dashboard (session izleme, config duzenleme)
- OpenTelemetry entegrasyonu
- MCP sunucu entegrasyonu
- Performans optimizasyonu
- Kapsamli test suite
- Plugin sistemi (deneysel)
- Ses destegi (deneysel)

### Gorev Listesi

| # | Gorev | Dosya(lar) | Bagimlilik | Tahmini Sure |
|---|-------|-----------|------------|-------------|
| 4.1 | Zamanlayici (APScheduler + SOP tetikleme) | `aethon/tools/scheduler.py` | Faz 3 | 4 saat |
| 4.2 | send_message tool (kanal-arasi mesajlasma) | `aethon/tools/messaging.py` | Faz 2 | 2 saat |
| 4.3 | Web dashboard — durum sayfasi | `aethon/ui/` | Faz 1 | 6 saat |
| 4.4 | Web dashboard — session izleme | `aethon/ui/` | 4.3 | 4 saat |
| 4.5 | Web dashboard — config duzenleme | `aethon/ui/` | 4.3 | 4 saat |
| 4.6 | TelemetryHookProvider (OpenTelemetry) | `aethon/agent/hooks/telemetry.py` | Faz 1 | 4 saat |
| 4.7 | MemoryGuardHook (hassas bilgi tespiti) | `aethon/agent/hooks/memory_guard.py` | Faz 2 | 3 saat |
| 4.8 | MCP sunucu entegrasyonu (dis tool kaynaklari) | `aethon/tools/mcp_integration.py` | Faz 1 | 6 saat |
| 4.9 | Performans optimizasyonu (caching, lazy loading) | Cesitli | Faz 1-3 | 6 saat |
| 4.10 | Kapsamli test suite (unit + integration) | `tests/` | Faz 1-3 | 8 saat |
| 4.11 | CONTEXT.md otomatik guncelleme | `aethon/agent/prompt.py` | Faz 1 | 3 saat |
| 4.12 | Plugin sistemi (deneysel) | `aethon/plugins/` | Faz 1 | 6 saat |
| 4.13 | Ses destegi — Bidi streaming (deneysel) | `aethon/channels/voice.py` | Faz 2 | 8 saat |
| 4.14 | Webhook destegi (dis tetikleyiciler) | `aethon/gateway/webhooks.py` | Faz 1 | 4 saat |

**Toplam tahmini sure: ~68 saat (surekli gelistirme)**

### Basari Kriterleri
- [ ] Sabah 9'da otomatik brifing geliyor (zamanlayici)
- [ ] Dashboard'dan aktif session'lar goruntuleniyor
- [ ] OpenTelemetry trace'leri gorulebiliyor
- [ ] MCP uzerinden dis tool kullanilabiliyor
- [ ] Tum testler geciyor
- [ ] Yanit suresi kabul edilebilir seviyede (< 30s basit gorevler)

---

## Oncelik Matrisi

```
P0 (Zorunlu — Faz 1):
  ✦ Proje iskeleti
  ✦ OllamaModel entegrasyonu
  ✦ CLI + WebChat adapterleri
  ✦ Temel agent + tool'lar
  ✦ Session yonetimi
  ✦ Guvenlik hook'lari

P1 (Onemli — Faz 2+3):
  ✦ Telegram, Discord, Slack, WhatsApp
  ✦ Multi-agent takim
  ✦ SOP sistemi
  ✦ Vektor hafiza
  ✦ Interrupt mekanizmasi

P2 (Guzellestirme — Faz 4):
  ✦ Zamanlayici
  ✦ Dashboard
  ✦ OpenTelemetry
  ✦ MCP entegrasyonu
  ✦ Plugin sistemi
  ✦ Ses destegi
```

---

## Risk Tablosu

| Risk | Olasilik | Etki | Azaltma |
|------|----------|------|---------|
| Qwen3-Coder-Next tool calling guvenilirsiz | Orta | Yuksek | Ollama native API kullan, format denetimi ekle |
| WhatsApp neonize kararlilik sorunu | Yuksek | Dusuk | whatsapp-web.js bridge alternatifi hazirla |
| Multi-agent token tuketimi yuksek | Orta | Orta | Agent-as-Tool varsayilan mod, Swarm sadece karmasik gorevlerde |
| Mac RAM yetersizligi (80B model) | Dusuk | Yuksek | Daha kucuk Ollama model (7B) fallback |
| Strands SDK breaking change | Dusuk | Orta | Versiyon pinleme, adapter layer |
| Session dosyalari buyuk | Dusuk | Dusuk | SummarizingConversationManager ile sinirla |

---

## Zaman Cizelgesi (Tahmini)

```
Hafta 1-2:  Faz 1 — Cekirdek Runtime
            ├── Proje iskeleti
            ├── Config + Model entegrasyonu
            ├── Agent Runtime + Hooks
            ├── CLI + WebChat adapterleri
            └── Gateway + Router

Hafta 3-4:  Faz 2 — Kanallar + Hafiza
            ├── Telegram + Discord adapterleri
            ├── Slack + WhatsApp adapterleri
            ├── Vektor hafiza
            ├── Session yonetimi
            └── Media destegi

Hafta 5-6:  Faz 3 — Multi-Agent + SOP
            ├── Uzman agent tanimlari
            ├── Delegate tool'lar + Orchestrator
            ├── Swarm + Graph modlari
            ├── SOP sistemi
            └── Interrupt mekanizmasi

Hafta 7+:   Faz 4 — Cilalama (surekli)
            ├── Zamanlayici
            ├── Dashboard
            ├── Optimizasyon
            └── Ileri ozellikler
```
