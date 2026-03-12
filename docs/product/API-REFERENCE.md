# AETHON — API Referansi

> Tum HTTP endpoint'leri, WebSocket protokolleri, webhook entegrasyonlari ve agent tool'lari.

---

## 1. WebChat Endpoint'leri

AETHON varsayilan olarak `http://127.0.0.1:18790` adresinde dinler.

### 1.1 WebChat UI

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/ui` | GET | WebChat arayuzu (HTML) |

**Ornek:**
```
GET http://127.0.0.1:18790/ui
```

### 1.2 WebSocket Chat

| Endpoint | Protokol | Aciklama |
|----------|----------|----------|
| `/ws/chat` | WebSocket | Gercek zamanli sohbet |

**Baglanti:**
```javascript
const ws = new WebSocket("ws://127.0.0.1:18790/ws/chat");
```

**Mesaj Gonderme:**
```json
"Merhaba, bugun ne yapacagiz?"
```

**Yanit Alma:**
```json
"Merhaba! Sana nasil yardimci olabilirim?"
```

WebSocket baglantisi metin tabanlidir. Client duz metin gonderir, sunucu duz metin dondurur.

---

## 2. Dashboard API

Dashboard aktif oldugunda (`dashboard.enabled: true`) asagidaki endpoint'ler kullanilabilir.

### 2.1 Dashboard UI

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/dashboard` | GET | Izleme paneli (HTML) |

**Ornek:**
```
GET http://127.0.0.1:18790/dashboard
```

Glassmorphism + cyberpunk neon temali izleme paneli. Oturumlar, hafiza, telemetri ve zamanlanmis gorevleri gosterir. 5 saniyede bir otomatik yenilenir.

### 2.2 Oturum Listesi

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/sessions` | GET | Aktif oturumlari listele |

**Yanit:**
```json
{
  "sessions": [
    {
      "session_id": "telegram:12345678",
      "agent_name": "AETHON"
    }
  ],
  "count": 1
}
```

### 2.3 Hafiza Istatistikleri

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/memory` | GET | Hafiza durumu ve son kayitlar |

**Yanit:**
```json
{
  "enabled": true,
  "count": 42,
  "entries": [
    {
      "id": 1,
      "content": "Python projesi icin asyncio kullan",
      "category": "preference",
      "created_at": "2026-03-12T10:30:00"
    }
  ]
}
```

### 2.4 Hafiza Arama

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/memory/search` | POST | Semantik hafiza arama |

**Istek:**
```json
{
  "query": "Python tercihleri"
}
```

**Yanit:**
```json
{
  "results": [
    {
      "id": 1,
      "content": "Python projesi icin asyncio kullan",
      "category": "preference",
      "similarity": 0.89
    }
  ]
}
```

### 2.5 Yapilandirma

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/config` | GET | Mevcut sistem yapilandirmasi |

**Yanit:**
```json
{
  "model": {
    "provider": "ollama",
    "model_id": "qwen3-coder-next",
    "host": "http://localhost:11434",
    "temperature": 1.0,
    "max_tokens": 16384
  },
  "memory": { "enabled": true, "..." : "..." },
  "channels": { "..." : "..." }
}
```

### 2.6 Zamanlanmis Gorevler

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/scheduler/jobs` | GET | Zamanlanmis gorev listesi |

**Yanit:**
```json
{
  "jobs": [
    {
      "job_id": "morning-brief",
      "sop_name": "morning-brief",
      "cron": "0 9 * * 1-5",
      "channel": "telegram",
      "next_run": "2026-03-13 09:00:00"
    }
  ]
}
```

### 2.7 Telemetri

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `/api/telemetry` | GET | Telemetri ozeti ve son metrikler |

**Yanit:**
```json
{
  "enabled": true,
  "summary": {
    "total_tool_calls": 156,
    "total_model_calls": 89,
    "error_count": 2,
    "avg_tool_duration": 0.45,
    "avg_model_duration": 3.21,
    "tool_success_rate": 0.987,
    "model_success_rate": 1.0
  },
  "metrics": [
    {
      "type": "tool",
      "name": "shell",
      "duration": 0.32,
      "status": "success",
      "timestamp": "2026-03-12T14:30:15"
    }
  ]
}
```

### 2.8 Canli Telemetri Stream

| Endpoint | Protokol | Aciklama |
|----------|----------|----------|
| `/ws/telemetry` | WebSocket | Gercek zamanli metrik akisi |

**Baglanti:**
```javascript
const ws = new WebSocket("ws://127.0.0.1:18790/ws/telemetry");
ws.onmessage = (e) => {
  const metric = JSON.parse(e.data);
  console.log(metric.type, metric.name, metric.duration);
};
```

**Metrik Formati:**
```json
{
  "type": "tool",
  "name": "shell",
  "duration": 0.32,
  "status": "success",
  "timestamp": "2026-03-12T14:30:15"
}
```

Sunucu her 2 saniyede bir yeni metrikleri push eder.

---

## 3. Webhook Endpoint'leri

Webhook aktif oldugunda (`webhook.enabled: true`) disaridan mesaj ve SOP tetiklemesi yapilabilir.

### 3.1 Kanal Bazli Webhook

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `POST /webhook/{channel}` | POST | Belirtilen kanala mesaj gonder |

**Ornek:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"text": "Merhaba AETHON!"}'
```

**Yanit:**
```json
{
  "status": "ok",
  "response": "Merhaba! Nasil yardimci olabilirim?"
}
```

### 3.2 SOP Tetikleyici

| Endpoint | Metod | Aciklama |
|----------|-------|----------|
| `POST /webhook/trigger` | POST | SOP calistir ve sonucu kanala gonder |

**Istek Govdesi:**

| Alan | Tip | Zorunlu | Aciklama |
|------|-----|---------|----------|
| `text` | string | Hayir | Mesaj metni |
| `sop_name` | string | Hayir | Calistirilacak SOP adi |
| `channel` | string | Hayir | Sonucun gonderilecegi kanal |
| `recipient` | string | Hayir | Alici ID |

**Ornek — SOP Tetikleme:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "sop_name": "morning-brief",
    "text": "Bugunun ozeti",
    "channel": "telegram",
    "recipient": "12345678"
  }'
```

**Ornek — Duz Mesaj:**
```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -d '{"text": "Proje durumu nedir?"}'
```

**Yanit:**
```json
{
  "status": "ok",
  "response": "Proje durumu: 3 acik gorev, 2 tamamlanan..."
}
```

### 3.3 HMAC-SHA256 Dogrulama

Webhook secret belirlendiginde (`webhook.secret` config'de), tum isteklerde `X-Aethon-Signature` header'i gereklidir.

**Imza Olusturma:**
```python
import hashlib, hmac

secret = "benim-gizli-anahtarim"
body = b'{"text": "Merhaba"}'
signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

# Header: X-Aethon-Signature: <signature>
```

```bash
curl -X POST http://127.0.0.1:18790/webhook/trigger \
  -H "Content-Type: application/json" \
  -H "X-Aethon-Signature: a1b2c3d4e5..." \
  -d '{"text": "Guvenli mesaj"}'
```

Secret bos ise (`""`) dogrulama devre disidir.

---

## 4. Agent Tool'lari

AETHON agent'inin kullandigi tum tool'lar. Agent bu tool'lari mesaj isleme sirasinda otomatik olarak kullanir.

### 4.1 Strands Dahili Tool'lar

| Tool | Import | Aciklama |
|------|--------|----------|
| `file_read` | `strands_tools` | Dosya oku |
| `file_write` | `strands_tools` | Dosya yaz |
| `editor` | `strands_tools` | Dosya duzenle (diff-tabanli) |
| `shell` | `strands_tools` | Komut satirinda calistir |
| `python_repl` | `strands_tools` | Python kodu calistir |
| `http_request` | `strands_tools` | HTTP istegi gonder |
| `calculator` | `strands_tools` | Matematiksel hesaplama |
| `think` | `strands_tools` | Icsel dusunce (yapilan planlama) |
| `current_time` | `strands_tools` | Mevcut tarih/saat |

### 4.2 Uzman Delegasyon Tool'lari

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `ask_coder` | `tools/delegate.py` | Kodlama gorevini kodcu uzmanina devret |
| `ask_researcher` | `tools/delegate.py` | Arastirma gorevini arastirmaciya devret |
| `ask_analyst` | `tools/delegate.py` | Analiz gorevini analiste devret |
| `ask_planner` | `tools/delegate.py` | Planlama gorevini planlayiciya devret |

**Parametre:**
- `task` (str): Uzmanin yapacagi gorev aciklamasi

**Calisma Sekli:** Ana agent gorevi uygun uzmana devreder. Uzman kendi tool'larini kullanarak gorevi tamamlar ve sonucu dondurur.

### 4.3 Hafiza Yonetim Tool'u

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `manage_memory` | `tools/memory_tool.py` | Uzun vadeli hafizayi yonet |

**Parametreler:**

| Parametre | Tip | Aciklama |
|-----------|-----|----------|
| `action` | str | `store`, `search`, `list`, `forget`, `count` |
| `content` | str | Hafizaya eklenecek icerik (store icin) |
| `category` | str | Kategori etiketi (store icin, opsiyonel) |
| `query` | str | Arama sorgusu (search icin) |
| `memory_id` | int | Silinecek kayit ID (forget icin) |

**Ornekler:**
```
# Hafizaya bilgi ekle
manage_memory(action="store", content="Kullanici Python 3.11 tercih ediyor", category="preference")

# Hafizada ara
manage_memory(action="search", query="Python tercihleri")

# Tum kayitlari listele
manage_memory(action="list")

# Belirli kaydi sil
manage_memory(action="forget", memory_id=5)

# Kayit sayisini ogren
manage_memory(action="count")
```

### 4.4 Baglam Yonetim Tool'u

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `update_context` | `tools/context_tool.py` | CONTEXT.md dosyasini yonet |

**Parametreler:**

| Parametre | Tip | Aciklama |
|-----------|-----|----------|
| `action` | str | `update`, `get`, `list` |
| `key` | str | Baglam anahtari |
| `value` | str | Baglam degeri (update icin) |

**Ornekler:**
```
# Baglam guncelle
update_context(action="update", key="Aktif Proje", value="AETHON v0.1.0 gelistirmesi")

# Baglam oku
update_context(action="get", key="Aktif Proje")

# Tum anahtarlari listele
update_context(action="list")
```

CONTEXT.md'ye `### Anahtar\nDeger` formatinda yazilir. Agent oturumlar arasi baglam bilgisini bu sekilde korur.

### 4.5 Mesajlasma Tool'u

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `send_message` | `tools/messaging.py` | Baska kanala mesaj gonder |

**Parametreler:**

| Parametre | Tip | Aciklama |
|-----------|-----|----------|
| `channel` | str | Hedef kanal (`telegram`, `discord`, `slack`, `webchat`) |
| `text` | str | Gonderilecek mesaj metni |
| `recipient` | str | Alici ID (opsiyonel, bos ise varsayilan) |

**Ornek:**
```
send_message(channel="telegram", text="Gorev tamamlandi!", recipient="12345678")
```

### 4.6 Zamanlayici Tool'lari

| Tool | Dosya | Aciklama |
|------|-------|----------|
| `schedule_task` | `tools/scheduler.py` | Cron tabanli gorev zamanla |
| `list_scheduled_jobs` | `tools/scheduler.py` | Zamanlanmis gorevleri listele |
| `remove_scheduled_job` | `tools/scheduler.py` | Zamanlanmis gorevi kaldir |

**schedule_task Parametreleri:**

| Parametre | Tip | Aciklama |
|-----------|-----|----------|
| `cron_expression` | str | Cron ifadesi (orn: `0 9 * * 1-5`) |
| `sop_name` | str | Calistirilacak SOP adi |
| `job_id` | str | Gorev ID (opsiyonel, otomatik olusturulur) |
| `channel` | str | Sonuc kanali (opsiyonel) |

**Cron Formati:** `dakika saat gun ay haftaGunu`

| Ornek | Anlami |
|-------|--------|
| `0 9 * * *` | Her gun saat 9:00 |
| `0 9 * * 1-5` | Hafta ici saat 9:00 |
| `30 18 * * 5` | Cuma 18:30 |
| `0 0 1 * *` | Her ayin 1'i gece yarisi |

---

## 5. SOP Komutlari

SOP'lar (Standard Operating Procedures) sohbette `/` on-ekiyle tetiklenir.

### 5.1 Dahili SOP'lar

| Komut | Aciklama |
|-------|----------|
| `/code-assist <gorev>` | Kod yazma, duzeltme, refactoring |
| `/pdd <gorev>` | Puzzle-Driven Development akisi |
| `/morning-brief` | Sabah brifing raporu |

### 5.2 SOP Calistirma

```
Kullanici: /code-assist Bu fonksiyona hata yakalama ekle
AETHON: [SOP adimlari izlenerek gorev tamamlanir]
```

### 5.3 Ozel SOP Olusturma

`~/.aethon/workspace/sops/` dizinine `.sop.md` uzantili dosya ekleyin:

```markdown
# Ozel SOP Adi

## Overview
Bu SOP ne yapar aciklamasi.

## Steps
1. Ilk adim aciklamasi
2. Ikinci adim aciklamasi
```

Dosya adi `benim-sop.sop.md` ise komut `/benim-sop` olur.

---

## 6. Guvenlik Katmani

### 6.1 Komut Engelleme

`security.blocked_commands` listesindeki komutlar otomatik engellenir:

```yaml
security:
  blocked_commands:
    - "rm -rf /"
    - "sudo "
    - "mkfs"
```

### 6.2 Kullanici Dogrulama

Kanal bazli izinli kullanici listesi:

```yaml
security:
  allowed_senders:
    telegram: ["12345678"]
    discord: ["98765432"]
```

### 6.3 Hafiza Korumasi (MemoryGuard)

`manage_memory` tool'unun `store` islemi sirasinda hassas bilgi otomatik engellenir:

- API key'ler (`api_key=...`)
- Sifreler (`password=...`)
- Token'lar (`secret=...`, `token=...`)
- SSH anahtarlari
- Ozel anahtar bloklari (PEM)
- Kredi karti numaralari
- SSN numaralari

Ozel pattern eklemek icin:

```yaml
memory_guard:
  custom_patterns:
    - "internal_secret=\\S+"
```

### 6.4 Onay Mekanizmasi

Tehlikeli tool'lar icin kullanici onay gereksinimi:

```yaml
approval:
  enabled: true
  requires_approval:
    - shell
    - file_write
```

---

## 7. Hata Kodlari

| HTTP Kodu | Anlami |
|-----------|--------|
| 200 | Basarili |
| 403 | Gecersiz HMAC imzasi (webhook) |
| 422 | Gecersiz istek govdesi |
| 500 | Sunucu hatasi |

WebSocket baglanti hatalari standart WebSocket close kodlarini kullanir.

---

## 8. Port Haritasi

| Servis | Port | Protokol |
|--------|------|----------|
| WebChat + Dashboard + Webhook + API | 18790 | HTTP/WS |
| Ollama | 11434 | HTTP |
| Telegram | - | HTTPS (outbound) |
| Discord | - | WSS (outbound) |
| Slack | - | WSS (outbound) |

Tum yerel servisler `127.0.0.1` adresine baglidir. `0.0.0.0` kullanilmaz.
