# OpenClaw - Kapsamli Teknik Referans Dokumani

> Son guncelleme: 2026-03-12
> Kaynaklar: OpenClaw Docs, GitHub Repo, Teknik Blog Yazilari, Guvenlik Raporlari, Wikipedia

---

## 1. GENEL BAKIS

OpenClaw, **kendi makinenizde calisan, acik kaynakli, otonom bir AI asistanidir.** Mesajlasma platformlari (WhatsApp, Telegram, Discord vb.) uzerinden erisilen bu sistem, AI modellerini gercek dunya gorevlerini yurutebilen bir agent'a donusturur.

- **Lisans:** MIT
- **Yaratici:** Peter Steinberger (Avusturyali gelistirici, PSPDFKit kurucusu)
- **Dil/Runtime:** Node.js 22+ (TypeScript/JavaScript)
- **Mimari:** Self-hosted Gateway + Embedded Pi Agent
- **GitHub Yildizi:** 145,000+ (Mart 2026)
- **Sponsorlar:** OpenAI, Vercel, Blacksmith, Convex

### 1.1 Tarihce

| Tarih | Isim | Olay |
|-------|------|------|
| Kasim 2025 | **Clawdbot** | Peter Steinberger tarafindan hafta sonu projesi olarak baslatildi |
| 27 Ocak 2026 | **Moltbot** | Anthropic'in ticari marka sikayeti uzerine yeniden adlandirildi |
| 29-30 Ocak 2026 | **OpenClaw** | Son isim degisikligi — acik kaynak ve istakoz mirasini yansitir |
| Ocak sonu 2026 | - | Viral populerlik patladi, Moltbook projesi ile |
| 14 Subat 2026 | - | Steinberger OpenAI'ye katilacagini acikladi, proje acik kaynak vakfina tasinacak |

---

## 2. MIMARI

### 2.1 Genel Yapi

OpenClaw bir "chatbot wrapper" degil, **AI agentlari icin bir isletim sistemi** olarak tasarlanmistir. Hub-and-spoke deseni kullanir:

```
                    +------------------+
                    |    Gateway       |
                    | (Control Plane)  |
                    | ws://127.0.0.1   |
                    |     :18789       |
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |         |         |         |         |
    +---------+ +------+ +-------+ +------+ +--------+
    |WhatsApp | |Tele- | |Discord| | CLI  | |macOS/  |
    |(Baileys)| |gram  | |(d.js) | |      | |iOS/    |
    |         | |(gram-| |       | |      | |Android |
    |         | | mY)  | |       | |      | |Nodes   |
    +---------+ +------+ +-------+ +------+ +--------+
                             |
                    +--------+---------+
                    |   Pi Agent       |
                    | (Embedded SDK)   |
                    | AgentSession     |
                    +------------------+
                             |
                    +--------+---------+
                    |   LLM Provider   |
                    | (Anthropic/OpenAI|
                    |  /Google/Ollama) |
                    +------------------+
```

### 2.2 Dort Katmanli Mimari

| Katman | Gorev | Konum |
|--------|-------|-------|
| **Gateway** | Mesaj yonlendirme, session yonetimi, erisim kontrolu | `src/gateway/server.ts` |
| **Integration** | Platform adapterleri (WhatsApp, Telegram, vb.) | Channel adaptorleri |
| **Execution** | Tool calistirma, sandbox, dosya islemleri | Pi Agent + OpenClaw tool'lari |
| **Intelligence** | LLM etkilesimi, context yonetimi, hafiza | Pi Agent Core + Providers |

### 2.3 Gateway Control Plane

- **Tek Node.js 22+ sureci**, `127.0.0.1:18789`'a baglanir (loopback-only)
- WebSocket sunucusu — tum platform baglantilarini yonetir
- **Session, presence ve sistem durumu icin tek dogru kaynak**
- JSON Schema tanimi ile strict dogrulama — bilinmeyen key'ler hata verir
- Event-driven mimari (poll-based degil)
- Config dosyasini izler, degisiklikleri otomatik uygular

### 2.4 Pi Agent (Cekirdek Agent Runtime)

OpenClaw **kendi agent runtime'ini uygulamaz.** Agent dongusunu — tool calling, context yonetimi, LLM etkilesimi — **Pi agent framework** uzerinden calistirir.

**Pi'nin Felsefesi:** "LLM'ler kod yazmada ve calistirmada cok iyiler, bunu kucakla."

**Pi'nin 4 Temel Tool'u:**

| Tool | Islem |
|------|-------|
| **Read** | Dosya okuma |
| **Write** | Dosya yazma |
| **Edit** | Dosya duzenleme |
| **Bash** | Shell komutu calistirma |

**Pi Paketleri (v0.49.3):**

| Paket | Gorev |
|-------|-------|
| `pi-ai` | LLM soyutlamalari, Model arayuzu, streaming yardimcilari, provider API'leri |
| `pi-agent-core` | Agent calistirma dongusu, tool orkestrasyon, mesaj tipleri |
| `pi-coding-agent` | Ust-seviye SDK: `createAgentSession`, `SessionManager`, `AuthStorage`, `ModelRegistry` |
| `pi-tui` | Terminal UI bilesenleri (lokal interaktif mod) |

**Anahtar Fark:** OpenClaw, Pi'yi subprocess olarak baslatmaz — dogrudan SDK uzerinden import eder ve `createAgentSession()` ile AgentSession olusturur.

### 2.5 Mesaj Akis Mimarisi

Uctan uca mesaj akisi 6 asamadan olusur:

1. **Ingestion (Alma):** Platform adapterleri gelen mesajlari parse eder (metadata cikarimli)
2. **Access Control & Routing:** Allowlist dogrulama, DM pairing kontrolleri, session tipi belirleme
3. **Context Assembly:** System prompt bilesimi, session gecmisi yukleme, semantik hafiza enjeksiyonu
4. **Model Invocation:** Birlestirilmis context provider'a stream edilir
5. **Tool Execution:** Tool call'lar yakalanir ve calistirilir (sandbox icinde olabilir)
6. **Response Delivery:** Ciktisi platform'a gore formatlanir, session dosyasina yazilir

### 2.6 Tool Pipeline (7 Katman)

Tool'lar su 7 isleme katmanindan gecer:

1. Pi'nin temel coding tool'lari (read, bash, edit, write)
2. OpenClaw degisimleri (sandbox icin ozel exec/process)
3. OpenClaw'a ozel tool'lar (messaging, browser, canvas, sessions, cron)
4. Kanal'a ozel tool'lar (Discord, Telegram, Slack, WhatsApp aksiyonlari)
5. **Policy filtreleme** (profil/provider/agent/group/sandbox politikalari)
6. Schema normalizasyonu (Gemini/OpenAI uyumlulugu)
7. AbortSignal sarmalama (iptal destegi)

**Tool Policy Oncelik Sirasi** (sonraki oncekini ezer):
```
Tool Profile → Provider Profile → Global Policy → Provider Policy → Agent Policy → Group Policy → Sandbox Policy
```

---

## 3. DESTEKLENEN PLATFORMLAR VE KANALLAR

### 3.1 Mesajlasma Kanallari

| Kanal | Kutuphane | Durum |
|-------|-----------|-------|
| WhatsApp | Baileys | Dahili |
| Telegram | grammY | Dahili |
| Slack | Bolt | Dahili |
| Discord | discord.js | Dahili |
| Google Chat | Chat API | Dahili |
| Signal | signal-cli | Dahili |
| iMessage (BlueBubbles) | BlueBubbles API | Dahili |
| IRC | - | Dahili |
| Microsoft Teams | - | Dahili |
| Matrix | - | Dahili |
| Feishu | - | Dahili |
| LINE | - | Dahili |
| Mattermost | - | Plugin |
| Nextcloud Talk | - | Dahili |
| Nostr | - | Dahili |
| Synology Chat | - | Dahili |
| Tlon | - | Dahili |
| Twitch | - | Dahili |
| Zalo / Zalo Personal | - | Dahili |
| WebChat | - | Dahili |

### 3.2 LLM Provider'lari

| Provider | Destek Durumu |
|----------|--------------|
| Anthropic (Claude) | Birincil destek |
| OpenAI (GPT) | Tam destek |
| Google (Gemini) | Tam destek |
| **Ollama (Yerel)** | Tam destek (native API) |
| Diger OpenAI-uyumlu | Desteklenir |

### 3.3 Cihaz Entegrasyonlari

| Platform | Ozellikler |
|----------|-----------|
| macOS | Menu bar uygulamasi, Voice Wake, Canvas |
| iOS | Node mode, Voice Wake |
| Android | Bildirimler, konum, SMS, fotograf, rehber, takvim, hareket |

---

## 4. KURULUM VE YAPILANDIRMA

### 4.1 Hizli Kurulum

```bash
# Gereksinim: Node 22+
npm install -g openclaw@latest
openclaw onboard --install-daemon    # Sihirbaz ile kurulum
openclaw channels login              # Kanal baglanma
openclaw gateway --port 18789        # Gateway baslatma
```

Kontrol paneli: `http://127.0.0.1:18789/`

### 4.2 Kaynaktan Kurulum

```bash
git clone https://github.com/openclaw/openclaw.git
cd openclaw
pnpm install
pnpm ui:build
pnpm build
pnpm openclaw onboard --install-daemon
pnpm gateway:watch  # Gelistirme dongusu
```

### 4.3 Guncelleme Kanallari

| Kanal | Aciklama | npm tag |
|-------|----------|---------|
| stable | Etiketli surumler | `latest` |
| beta | On-surum | `beta` |
| dev | main branch head | `dev` |

Degistirme: `openclaw update --channel stable|beta|dev`

### 4.4 Yapilandirma Dosyasi

Konum: `~/.openclaw/openclaw.json` (JSON5 formati — yorum ve sondaki virgul destekler)

**Yapilandirma Yontemleri:**
1. **CLI:** `openclaw config get/set/unset`
2. **Kontrol Paneli:** `http://127.0.0.1:18789` uzerinden form + Raw JSON editor
3. **Dosya:** `~/.openclaw/openclaw.json` direkt duzenleme (Gateway dosyayi izler, otomatik uygular)

### 4.5 Temel Yapilandirma Bolumleri

#### Agents & Models
```json
{
  "agents": {
    "defaults": {
      "workspace": "/path/to/workspace",
      "model": {
        "primary": "anthropic/claude-sonnet-4-5",
        "fallbacks": ["openai/gpt-4o"]
      },
      "models": {},
      "imageMaxDimensionPx": 1200,
      "sandbox": { "mode": "off|non-main|all" },
      "heartbeat": { "every": "...", "target": "...", "directPolicy": "..." }
    },
    "list": []
  }
}
```

#### Channels
```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "dmPolicy": "pairing|allowlist|open|disabled",
      "allowFrom": ["+905551234567"],
      "groupPolicy": "...",
      "groupAllowFrom": []
    },
    "telegram": { ... },
    "discord": { ... }
  }
}
```

#### Sessions
```json
{
  "session": {
    "dmScope": "main|per-peer|per-channel-peer|per-account-channel-peer",
    "threadBindings": { "idleLimit": "...", "ageLimit": "..." },
    "reset": { "mode": "daily", "timing": "..." }
  }
}
```

#### Otomasyon
```json
{
  "cron": {
    "enabled": true,
    "maxConcurrentRuns": 2,
    "sessionRetention": "...",
    "runLog": "..."
  },
  "hooks": {
    "enabled": true,
    "token": "...",
    "path": "...",
    "mappings": {}
  }
}
```

#### Gateway
```json
{
  "gateway": {
    "port": 18789,
    "reload": "hybrid|hot|restart|off",
    "auth": { ... }
  }
}
```

### 4.6 Ollama Entegrasyonu (Yerel Model)

```bash
# 1. Ollama kur ve modeli indir
ollama pull qwen3-coder-next

# 2. Ortam degiskeni ayarla
export OLLAMA_API_KEY="ollama-local"

# 3. VEYA config'de ayarla
openclaw config set models.providers.ollama.apiKey "ollama-local"
```

**Otomatik Kesif (Auto-Discovery):**
- `OLLAMA_API_KEY` ayarlandiysa ve explicit config yoksa
- `/api/tags` ve `/api/show` endpoint'lerini sorgular
- Sadece `tools` yetenegi bildiren modelleri kesfeder
- Tum maliyetler $0 olarak ayarlanir

**Manuel Yapilandirma:**
```json
{
  "models": {
    "providers": {
      "ollama": {
        "baseUrl": "http://127.0.0.1:11434",
        "apiKey": "ollama-local",
        "api": "ollama",
        "models": [{
          "id": "qwen3-coder-next",
          "name": "Qwen3 Coder Next",
          "reasoning": false,
          "input": ["text"],
          "cost": { "input": 0, "output": 0 },
          "contextWindow": 262144,
          "maxTokens": 65536
        }]
      }
    }
  }
}
```

**KRITIK:** URL'ye `/v1` EKLEMEYIN. `/v1` yolu OpenAI-uyumlu modu kullanir ve tool calling guvenilir degildir. Native Ollama API (`/api/chat`) kullanin.

**API Modlari:**

| Mod | URL | Tool Calling | Streaming |
|-----|-----|-------------|-----------|
| Native (Onerilen) | `http://host:11434` | Tam destek | Tam destek |
| OpenAI-Compatible | `http://host:11434/v1` | Guvenilir degil | Sorunlu olabilir |

---

## 5. SESSION YONETIMI

### 5.1 Session Tipleri (Guvenlik Sinirlari)

Session'lar sadece konusma konteyneri degil, **guvenlik sinirlaridir:**

| Session Tipi | ID Formati | Sandbox |
|--------------|-----------|---------|
| Main | `agent:<agentId>:main` | Yok — tam host erisimi |
| DM | `agent:<agentId>:<channel>:dm:<id>` | Varsayilan: aktif |
| Group | `agent:<agentId>:<channel>:group:<id>` | Varsayilan: aktif |

### 5.2 Persistence

- Session'lar **JSONL dosyalari** olarak saklanir (agac yapisi, parent-child baglama)
- **Append-only event log'lari** — dallanma ve gecmis inceleme destegi
- `SessionManager.open()` ile dosya islemleri
- Cache mekanizmasi ile tekrarlanan parse'lama onlenir

### 5.3 Context Yonetimi

- **History Limiting:** Kanal tipine gore konusma gecmisi kisilir (DM vs Group farkli limitler)
- **Auto-Compaction:** Context tasmasi durumunda otomatik tetiklenir
- **Memory Flush:** Onemli detaylar kalici hafiza dosyalarina terfi ettirilir
- Manuel compaction: Yapilandirilmis ozetleme destegi

### 5.4 Inter-Agent Iletisim

| Tool | Islem |
|------|-------|
| `sessions_list` | Aktif session'lari kesfetme |
| `sessions_send` | Diger session'lara mesaj gonderme |
| `sessions_history` | Diger session'lardan transcript alma |
| `sessions_spawn` | Yeni session olusturma (is delegasyonu) |

---

## 6. SKILLS SISTEMI

### 6.1 Genel Yapi

Skill'ler **Markdown dosyalardir** — `SKILL.md` icinde YAML frontmatter ve talimatlar icerirler.

**Neden Markdown?**
- Kod-tabanli degil, token-verimli
- Gerektigi zaman yuklenir (her session'da degil)
- MCP'den daha verimli
- Agent kendi skill'lerini yazabilir/degistirebilir (self-modifying)

### 6.2 SKILL.md Formati

```markdown
---
name: skill-adi
description: Skill'in ne yaptigi
user-invocable: true
disable-model-invocation: false
command-dispatch: tool
command-tool: tool_adi
command-arg-mode: raw
metadata:
  openclaw:
    always: false
    emoji: "🔧"
    os: [darwin, linux, win32]
    requires:
      bins: [git, docker]
      anyBins: [chrome, chromium]
      env: [GITHUB_TOKEN]
      config: [channels.telegram.enabled]
    primaryEnv: MY_API_KEY
    skillKey: my-skill
    install:
      - name: "Bagimliligi Kur"
        command: "npm install -g something"
---

# Skill Talimatlari

Burada agent'a ne yapmasini istediginizi dogal dilde yazarsiniz.
Agent bu talimatlari okur ve tool'larini kullanarak gorevi yerine getirir.
```

### 6.3 Frontmatter Alanlari

| Alan | Tip | Varsayilan | Aciklama |
|------|-----|-----------|----------|
| `name` | string | zorunlu | Skill tanimlayicisi |
| `description` | string | zorunlu | Kisa aciklama |
| `homepage` | string | - | macOS UI'da gosterilen URL |
| `user-invocable` | boolean | true | Slash komutu olarak erisilebilir mi |
| `disable-model-invocation` | boolean | false | Model prompt'undan haric tut ama kullanici cagirabilir |
| `command-dispatch` | string | - | `tool` olarak ayarlarsa modeli atlar, dogrudan tool calistirir |
| `command-tool` | string | - | `command-dispatch: tool` durumunda calistirilan tool |
| `command-arg-mode` | string | `raw` | Ham arguman string'ini tool'a iletir |
| `metadata` | JSON | - | Gating ve yapilandirma icin tek satirlik JSON objesi |

### 6.4 Uc Katmanli Skill Sistemi

| Katman | Konum | Oncelik | Aciklama |
|--------|-------|---------|----------|
| **Workspace** | `<workspace>/skills` | En yuksek | Kullaniciya ait, diger ikisini ezer |
| **Managed/Local** | `~/.openclaw/skills` | Orta | Yerel override'lar |
| **Bundled** | npm paketi icinde | En dusuk | OpenClaw ile gelen varsayilan skill'ler |

Ek klasorler: `skills.load.extraDirs` config ayari ile (en dusuk oncelik)

### 6.5 Skill Yasam Dongusu

1. OpenClaw, **session basladiginda** uygun skill'lerin anlIk goruntusunu alir
2. Sonraki tur'larda bu listeyi yeniden kullanir
3. Skills watcher aktifse veya yeni remote node gelirse session ortasinda yenileme olur
4. Uygun skill'ler, system prompt'a kompakt XML olarak enjekte edilir

**Token Etkisi:**
- Temel ek yuk (en az 1 skill varken): 195 karakter
- Skill basina: 97 karakter + XML-escaped alanlarin uzunlugu
- Kaba tahmin: ~4 karakter/token (OpenAI tokenizer'larinda)

### 6.6 ClawHub (Skill Marketi)

- **URL:** https://clawhub.com
- **Toplam Skill:** 13,729+ (28 Subat 2026 itibariyle)
- Skill yukleme: `clawhub install <skill-slug>`
- Guncelleme: `clawhub update --all`
- Yayinlama: `clawhub sync --all`
- Varsayilan kurulum: `./skills` (mevcut calisma dizini)

**GUVENLIK UYARISI:** 824+ zararli skill tespit edilmis (Subat 2026 itibariyle). Ucuncu taraf skill'leri **guvenilmeyen kod** olarak degerlendirilmelidir.

---

## 7. SYSTEM PROMPT BILESIMI

OpenClaw'in system prompt'u birden fazla katmanli kaynaktan birlestirilir:

```
Workspace Config (AGENTS.md)
  → SOUL.md (kisilik)
  → TOOLS.md (kullanici konvansiyonlari)
  → Dinamik Skill'ler (secici enjeksiyon)
  → Session Gecmisi
  → Hafiza Arama Sonuclari
  → Otomatik-uretilmis Tool Tanimlamalari
```

`buildAgentSystemPrompt()` fonksiyonu su bolumleri birlestirir:
- Tooling spesifikasyonlari ve cagri stili
- Guvenlik korumali (safety guardrails)
- OpenClaw CLI referansi
- Skills yapilandirmasi
- Dokumantasyon ve workspace detaylari
- Sandbox kisitlamalari
- Mesajlasma yonergeleri (media, ses, reply tag'lari)
- Sessiz yanit mekanikleri
- Heartbeat beklentileri
- Runtime metadatasi
- Opsiyonel hafiza ve reaksiyon sistemleri

### 7.1 Workspace Dosyalari

| Dosya | Islem |
|-------|-------|
| `AGENTS.md` | Workspace yapilandirmasi |
| `SOUL.md` | Agent kisiligi tanimlamasi |
| `TOOLS.md` | Kullanici konvansiyonlari ve tercihleri |

Bu yaklasim, kaynak koda dokunmadan dosya duzenlemeleri ile davranis degistirmeye olanak tanir.

---

## 8. HAFIZA SISTEMI

### 8.1 Depolama

- **SQLite veritabani:** `~/.openclaw/memory/<agentId>.sqlite`
- Vector embedding'ler ile zenginlestirilmis

### 8.2 Arama

Hibrit arama:
1. **Vector similarity** (semantik eslestirme)
2. **BM25 keyword** relevance

### 8.3 Embedding Provider Onceligi

1. Yapilandirilmissa yerel embedding modeli
2. OpenAI embedding'leri (API key varsa)
3. Gemini embedding'leri (API key varsa)
4. Hafiza aramasi devre disi (hicbiri yoksa)

### 8.4 Hafiza Dosyalari

| Dosya | Islem |
|-------|-------|
| `MEMORY.md` | Uzun vadeli curated bilgiler (sadece main session) |
| `memory/YYYY-MM-DD.md` | Gunluk calisma kayitlari |
| Session transcript indeksleme | `experimental.sessionMemory` ile opsiyonel |

---

## 9. SANDBOX VE IZOLASYON

### 9.1 Docker Tabanli Sandbox

- **Granularite:** Per-session (en guclu), per-agent, veya paylasimli
- **Host erisimi:** Salt-okunur workspace gorumleri, secici bind mount'lar, veya tam izolasyon
- **Ag erisimi:** Yapilandirilabilir, varsayilan olarak kapali
- **Kaynak limitleri:** Container basina CPU ve bellek kisitlamalari
- Sandbox sadece tool calistirmaya uygulanir (Gateway'e degil)
- Container'lar gecicidir — calistirma icin olusturulur, sonra yok edilir

### 9.2 Sandbox Modlari

| Mod | Aciklama |
|-----|----------|
| `off` | Sandbox kapali — tum session'lar tam erisimli |
| `non-main` | Main haricindeki session'lar sandbox icinde |
| `all` | Tum session'lar (main dahil) sandbox icinde |

---

## 10. SES VE CANVAS

### 10.1 Ses Entegrasyonu

- **Voice Wake:** macOS, iOS, Android'de her zaman acik algilama
- **Talk Mode:** Kesintisiz gidis-gelis diyalog (interrupt algilama ile)
- **Isleme:** ElevenLabs TTS + sistem TTS fallback
- Ozel wake phrase destegi

### 10.2 Canvas (A2UI - Agent-to-UI)

- Ayri sunucu sureci (varsayilan port: 18793)
- Gateway'den izole (crash containment ve guvenlik siniri)
- A2UI attribute'lari — agent-uretilen HTML'de JavaScript olmadan interaktif elemanlar
- Client etkilesim callback'lari → agent'a tool call olarak iletilir
- Platform destegi: macOS WebKit, iOS Swift UI, Android WebView, web tarayicilar

---

## 11. OTOMASYON

### 11.1 Cron Jobs

Config-tabanli zamanlama (orn: her sabah 9'da gunluk ozet):

```json
{
  "cron": {
    "enabled": true,
    "maxConcurrentRuns": 2
  }
}
```

### 11.2 Webhooks

Dis tetikleme noktalari:
- Gmail Pub/Sub entegrasyonu
- Ozel webhook endpoint'leri
- Mapping yapilandirmasi ile istek-session eslestirme

### 11.3 Heartbeat

Agent periyodik olarak check-in yapar:
```json
{
  "heartbeat": {
    "every": "30m",
    "target": "main",
    "directPolicy": "..."
  }
}
```

---

## 12. GENISLETILEBILIRLIK

### 12.1 Plugin Tipleri

| Tip | Islem |
|-----|-------|
| **Channel Plugin** | Ek mesajlasma platformlari |
| **Memory Plugin** | Alternatif depolama backend'leri (vector store, knowledge graph) |
| **Tool Plugin** | Ozel yetenekler — `api.registerTool()` ile kayit |
| **Provider Plugin** | Ozel LLM provider'lar veya self-hosted modeller |

Plugin kesfetme: workspace paketlerinde `openclaw.extensions` alanini tarar, schemalara gore dogrular, ve yapilandirilmissa hot-load yapar.

### 12.2 Pi Extension Sistemi

| Extension Event | Islem |
|----------------|-------|
| `context` | LLM gormeden once mesajlari yeniden yaz |
| `session_before_compact` | Ozetlemeyi ozellestir |
| `tool_call` | Tool cagrilarini yakala veya engelle |
| `before_agent_start` | Context enjekte et veya prompt'u degistir |
| `session_start` / `session_switch` | Session olaylarina tepki ver |

**Mevcut OpenClaw Extension'lari:**
- **Compaction Safeguard:** Adaptif token butceleme, tool hatasi ozetleri, dosya islemi izleme
- **Context Pruning:** Cache-TTL tabanli budama, token butce farkindagi

### 12.3 Provider'a Ozel Islemler

| Provider | Ozel Islem |
|----------|-----------|
| Anthropic | Reddetme temizleme, ardisik roller icin tur dogrulama |
| Google/Gemini | Tur siralama duzeltmeleri, tool schema sanitizasyonu |
| OpenAI | apply_patch tool destegi, thinking seviyesi dusurme fallback |

---

## 13. GUVENLIK

### 13.1 Ag Izolasyonu

- Gateway varsayilan olarak **loopback-only** baglanir (`127.0.0.1`)
- Uzaktan erisim icin acik tunelleme gerekir
- **KRITIK:** `0.0.0.0` gorurseniz gateway ag'a aciktir — hemen duzeltilmeli

### 13.2 Kimlik Dogrulama Katmanlari

| Katman | Mekanizma |
|--------|-----------|
| Gateway | Token veya sifre tabanli (loopback olmayan baglantilar icin) |
| Cihaz | Kriptografik imzalama ile cihaz eslestirme |
| Yerel | Yerel baglantilar otomatik onay |
| Uzak | Challenge-response gerektiren uzak baglantilar |

### 13.3 Kanal Seviyesi Erisim Kontrolu

- **DM Policy Modlari:**

| Mod | Aciklama |
|-----|----------|
| `pairing` (varsayilan) | Bilinmeyen gondericiler mesaj islenmeden once kod alir |
| `allowlist` | Sadece izin listesindeki kullanicilar |
| `open` | Herkese acik (TEHLIKELI) |
| `disabled` | DM kapali |

- Grup mention gereksinimleri ve gruba ozel allowlist'ler
- `openclaw doctor` komutu riskli DM politikalarini tespit eder

### 13.4 Prompt Injection Savunmasi

- Context ayristirmasi: kullanici mesajlari sistem talimatlarindan ayrik tutulur
- Tool sonuclari yapilandirilmis formatlarda sarmalanir
- Model onerisi: en yeni nesil modeller (Claude Opus 4.5 onerilir)
- Telafi kontrolleri: salt-okunur tool'lar, siki allowlist'ler, kucuk modeller icin sandbox

---

## 14. BILINEN GUVENLIK ACIKLARI VE OLAYLAR

### 14.1 CVE-2026-25253 (ClawJacked) — CVSS 8.8

**Kesfeden:** Oasis Security
**Tarih:** 26 Subat 2026 aciklanma, 24 saat icinde yama (v2026.2.25)

**Saldiri Zinciri:**
1. Kurban herhangi bir saldirgan kontrollü (veya ele gecirilmis) web sitesini ziyaret eder
2. Sayfadaki JavaScript, localhost'ta OpenClaw Gateway portuna WebSocket baglantisi acar
3. Tarayicilar cross-origin WebSocket baglantilerini localhost'a engellemez
4. Script, gateway sifresini saniyede yuzlerce denemeyle brute-force yapar
5. Gateway'in rate limiter'i localhost baglantilerini muaf tutar
6. Kimlik dogrulama sonrasi, script sessizce guvenilir cihaz olarak kaydolur
7. Gateway, localhost'tan cihaz eslestirmelerini kullanici onay olmadan otomatik kabul eder

**Etki:** Tam agent kontrolu — yapIlandirma verisi, bagli cihazlar, log'lar, ve agent'in tum yetkileri (kod tabanlari, entegrasyonlar, kimlik bilgileri)

### 14.2 ClawHub Tedarik Zinciri Saldirisi

- Arastirmaci 2,857 skill'den **341 zararli** skill tespit etti
- 335'i tek koordineli operasyona izlendi: **ClawHavoc**
- 16 Subat 2026 itibariyle: **824+ onaylanmis zararli skill** / 10,700+ skill kaydi
- Kripto cuzdani calan skill'ler dahil

### 14.3 Diger Bilinen Sorunlar

| Sorun | Detay |
|-------|-------|
| **Acik API Anahtarlari** | Yanlis yapilandirilmis dagintimlarda sifrelenmemis kimlik bilgileri |
| **Paylasimli Global Context** | Birden fazla kullanici ayni "main" session'i paylasiyor — bir kullanicinin env var'lari ve dosyalari digerine acik |
| **Grup Chat Tool Kotuye Kullanimi** | Grup session'lari uygun sandbox ve tool kisitlamalarindan yoksun |
| **Prompt Injection** | E-postalar, web sayfalari, ucuncu taraf skill'ler uzerinden zararli talimat enjeksiyonu |
| **Cross-Session Veri Sizintisi** | Bir session'da olusturulan dosyalar, workspace yapilandirma sorunu nedeniyle izole session'lardan erisilebilir |
| **Self-Modifying Davranis** | Agent kendi davranisini, hafizasini, skill'lerini otonom olarak degistirebilir — prompt injection ile birleste tehlikeli |
| **Genis Sistem Izinleri** | Agent, kullanici hesabinizin tum yetkileriyle calisir — tam disk, terminal, ag erisimi |
| **Kalici Hafiza Zehirlenmesi** | Haftalik context biriktiren persistent hafiza, sanitizasyon olmadan |
| **Moltbook Veritabani Ihlali** | 2.8 milyon AI agent'in veritabani ifsa oldu — herhangi birinin kontrolu ele gecilebilir |

### 14.4 Guvenlik Onerileri

1. **Sandbox modunu `non-main` veya `all` olarak ayarlayin**
2. DM scope'u `per-peer` veya `per-account-channel-peer` olarak yapilandirin
3. Grup etkilesimleri icin `workspaceAccess: "none"` kullanin
4. Siki tool allowlist'leri uygulayin
5. Kontrol UI'yi ozel aglar arkasina TLS ile alin
6. Dis dokumanlari tool-etkin sistemlere vermeden once salt-okunur araci agent uzerinden isleyin
7. Sirlari prompt'larda degil ortam degiskenlerinde saklayin
8. Duzenli olarak hafizayi denetleyin ve temizleyin
9. Ucuncu taraf skill'leri etkinlestirmeden once okuyun
10. Docker container'lar icinde izole ortamda calistirin
11. `openclaw doctor` komutunu duzenli olarak calistirin

---

## 15. DAGITIM DESENLERI

### 15.1 Yerel Gelistirme

- Her sey gelistirici makinesinde
- Kimlik dogrulama gereksiz
- Hot reload aktif

### 15.2 Production macOS

- LaunchAgent arka plan servisi
- Menu bar uygulamasi ile yasam dongusu kontrolu
- Native iMessage destegi
- Voice Wake

### 15.3 Uzak VPS/Linux

**Secenek A (SSH Tunnel):**
```bash
ssh -N -L 18789:127.0.0.1:18789 user@vps
```

**Secenek B (Tailscale Serve):**
Tailnet-only HTTPS, tunel yonetimi olmadan

### 15.4 Fly.io Container

Docker-yonetilen dagitim, kalici volume'ler, public HTTPS endpoint — guclu kimlik dogrulama gerektirir

### 15.5 Tailscale Entegrasyonu

Otomatik yapilandirilabilir:
- **Serve modu:** Tailnet-only erisim
- **Funnel modu:** Public erisim
- Opsiyonel sifre kimlik dogrulama

---

## 16. VERI DEPOLAMA YAPISI

```
~/.openclaw/
  ├── openclaw.json          # Ana yapilandirma (JSON5)
  ├── sessions/              # Session basina append-only event log'lari
  ├── memory/
  │   └── <agentId>.sqlite   # Vector embedding'ler ve semantik indeks
  ├── credentials/           # Platform auth token'lari (0600 izinler)
  ├── skills/                # Managed/local skill'ler
  └── ...

<workspace>/
  ├── AGENTS.md              # Workspace yapilandirmasi
  ├── SOUL.md                # Agent kisiligi
  ├── TOOLS.md               # Kullanici konvansiyonlari
  ├── MEMORY.md              # Kalici hafiza
  ├── memory/
  │   └── YYYY-MM-DD.md      # Gunluk kayitlar
  └── skills/                # Workspace skill'leri (en yuksek oncelik)
```

---

## 17. YAPILANDIRMA ONCELIGI

```
Ortam Degiskenleri > Config Dosyasi > Varsayilan Degerler
```

Bu, hassas token'larin ortam degiskenlerinde guvenli islenmesini saglar.

---

## 18. KAYNAKLAR

### Resmi
- Web sitesi: https://openclaw.ai
- Dokumantasyon: https://docs.openclaw.ai
- GitHub: https://github.com/openclaw/openclaw
- ClawHub: https://clawhub.com
- Discord: https://discord.gg/clawd

### Guvenlik Raporlari
- Oasis Security (ClawJacked): https://www.oasis.security/blog/openclaw-vulnerability
- CrowdStrike: https://www.crowdstrike.com/en-us/blog/what-security-teams-need-to-know-about-openclaw-ai-super-agent/
- Giskard: https://www.giskard.ai/knowledge/openclaw-security-vulnerabilities-include-data-leakage-and-prompt-injection-risks
- Microsoft Security: https://www.microsoft.com/en-us/security/blog/2026/02/19/running-openclaw-safely-identity-isolation-runtime-risk/
- DigitalOcean: https://www.digitalocean.com/resources/articles/openclaw-security-challenges
- Kaspersky: https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/

### Mimari Analizleri
- Pi Agent (Armin Ronacher): https://lucumr.pocoo.org/2026/1/31/pi/
- Mimari Genel Bakis: https://ppaolo.substack.com/p/openclaw-system-architecture-overview
- DEV Community: https://dev.to/ialijr/lessons-from-openclaws-architecture-for-agent-builders-1j93
- Nader Dabit (Pi Framework): https://nader.substack.com/p/how-to-build-a-custom-agent-framework

### Tarihce
- Wikipedia: https://en.wikipedia.org/wiki/OpenClaw
- Fortune: https://fortune.com/2026/02/19/openclaw-who-is-peter-steinberger-openai-sam-altman-anthropic-moltbook/
