# AETHON — Baslangic Kilavuzu

> Kurulumdan ilk mesaja kadar adim adim rehber.

---

## 1. Gereksinimler

| Gereksinim | Minimum |
|------------|---------|
| **Python** | 3.10+ |
| **Ollama** | En guncel |
| **RAM** | 16 GB (32 GB onerilen) |
| **Disk** | 50 GB (model icin) |
| **OS** | macOS (Apple Silicon onerilen) |

---

## 2. Kurulum

### 2.1 Ollama Kur

```bash
# Ollama'yi yukle (eger yoksa)
brew install ollama

# Ollama'yi baslat
ollama serve
```

### 2.2 Modelleri Indir

```bash
# Ana model — agent beyni
ollama pull qwen3-coder-next

# Embedding modeli — hafiza icin
ollama pull nomic-embed-text
```

### 2.3 AETHON'u Kur

```bash
# Projeyi klonla
git clone <repo-url> aethon
cd aethon

# Bagimliliklari yukle
pip install -e ".[all]"
```

---

## 3. Yapilandirma

### 3.1 Varsayilan Config

Ilk calistirmada AETHON otomatik olarak `~/.aethon/` dizinini ve varsayilan dosyalari olusturur. Ozel yapilandirma icin:

```bash
mkdir -p ~/.aethon
```

`~/.aethon/config.yaml` olustur:

```yaml
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

multi_agent:
  enabled: true

sops:
  enabled: true

telemetry:
  enabled: true

dashboard:
  enabled: true
```

### 3.2 Workspace Dosyalari

`~/.aethon/workspace/` dizininde 3 temel dosya:

| Dosya | Amac |
|-------|------|
| `SOUL.md` | Agent'in kisilik ve davranis kurallari |
| `TOOLS.md` | Kullanici tercihleri ve kodlama standartlari |
| `CONTEXT.md` | Mevcut proje/baglam bilgisi (otomatik guncellenir) |

---

## 4. Baslatma

```bash
python -m aethon start
```

Konsol ciktisi:

```
AETHON baslatiliyor...

  Provider: ollama
  Model: qwen3-coder-next
  WebChat: http://127.0.0.1:8080
  Memory: nomic-embed-text (aktif)
  Multi-Agent: aktif
  SOP'lar: 3 adet
  Zamanlayici: aktif
  Telemetri: aktif
  Dashboard: http://127.0.0.1:8080/dashboard
  Kanallar: CLI, WebChat
```

---

## 5. Ilk Mesajini Gonder

### CLI'dan

AETHON basladiktan sonra terminal'e yaz:

```
> Merhaba, sen kimsin?
```

### WebChat'ten

Tarayicida ac: `http://127.0.0.1:8080`

### Telegram'dan

1. `config.yaml`'a token ekle:
   ```yaml
   channels:
     telegram:
       enabled: true
       token: "${TELEGRAM_BOT_TOKEN}"
   ```

2. Token'i environment variable olarak ayarla veya `~/.aethon/credentials/telegram.env`'ye kaydet

3. AETHON'u yeniden baslat

---

## 6. SOP Kullanimi

Hazir SOP'lari tetikle:

```
/code-assist login sayfasi implement et
/pdd yeni e-ticaret backend tasarla
/codebase-summary projeyi dokumante et
```

### Ozel SOP Olustur

`~/.aethon/workspace/sops/morning-brief.sop.md`:

```markdown
# Morning Brief

## Overview
Her sabah kisa brifing hazirla.

## Steps
1. Bugunun tarihini ve gununu kontrol et
2. Oncelikli gorevleri listele
3. Kisaca ozet hazirla
```

Tetikle: `/morning-brief`

---

## 7. Dashboard

Tarayicida ac: `http://127.0.0.1:8080/dashboard`

Goreceklerin:
- **Oturumlar** — Aktif session'lar
- **Hafiza** — Uzun vadeli hafiza kayitlari
- **Telemetri** — Tool/Model cagri istatistikleri
- **Zamanlanmis Gorevler** — Cron job'lar
- **Canli Metrikler** — Gercek zamanli WebSocket akisi

---

## 8. Sonraki Adimlar

- Telegram/Discord/Slack kanallarini yapilandir → bkz. `docs/product/CONFIGURATION.md`
- Webhook entegrasyonu kur → bkz. `docs/product/API-REFERENCE.md`
- Zamanlayici ile otomatik gorevler olustur
- Ozel SOP'lar yaz
- MCP sunuculari bagla
