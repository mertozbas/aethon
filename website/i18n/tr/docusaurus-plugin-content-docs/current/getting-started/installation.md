---
id: installation
title: Kurulum
sidebar_label: Kurulum
---

# Kurulum

Yeni bir makinede ilk kez kurulum için eksiksiz bir rehber. **Tek bir** kurulum
yolu seçin, bir model arka ucu yapılandırın, ardından başlayın.

## Hızlı başlangıç

En hızlı yol — kurun, sihirbazı çalıştırın, tarayıcınızda sohbet edin:

```bash
pip install aethon-ai      # PyPI paketi; komut + import "aethon"
aethon init                # kurulum sihirbazı: bir sağlayıcı seçin, anahtar yapıştırın (ya da yerele geçin)
aethon start               # gateway'i + etkin tüm kanalları başlatır
# → http://127.0.0.1:18790 adresini açın  (WebChat)  ·  canlı pano için /dashboard
```

Sohbete başlamak için bu kadarı yeterli (terminal CLI de varsayılan olarak
açıktır). **Ancak bu hızlı yol, paketle gelen `codex-proxy`'yi (ChatGPT-Pro arka
ucu) içermez** — onun için aşağıdaki **klonlama** yolunu (Yol A) izleyin.

## Ön koşullar

- **Python 3.10, 3.11 veya 3.12** — `python3 --version` ile kontrol edin. (macOS'te: `brew install python`; Debian/Ubuntu'da: `sudo apt install python3 python3-venv python3-pip`.)
- **git** — yalnızca klonlama yolu (Yol A) için gerekir.
- **Bir model arka ucu — birini seçin** (bunu 2. adımda kurarsınız):
  - bir **OpenAI API anahtarı** (en basiti), **ya da**
  - paketle gelen **`codex-proxy`** aracılığıyla **ChatGPT Pro** — **Node.js 18+** gerektirir (`node --version`), **ya da**
  - tamamen yerel bir **Ollama** modeli — anahtar yok, çevrimdışı çalışır.
- **(İsteğe bağlı) [Ollama](https://ollama.com)** — varsayılan vektör-bellek gömmeleri için. `aethon init` onu kurup modeli sizin için indirebilir; bellek OpenAI gömmeleriyle de çalışır ya da tamamen kapatabilirsiniz.

:::note
AETHON'un yazdığı her şey **`~/.aethon/`** altında durur (yapılandırma, oturumlar,
bellek, loglar). `aethon` komutu dışında hiçbir şey global değildir.
:::

## Yol A — Klonla ve kur (önerilen)

Paketle gelen `codex-proxy` dahil **her şeyi** alır; güncellemeler bir `git pull`'dan ibarettir.

```bash
# 1. Depoyu klonlayın
git clone https://github.com/mertozbas/aethon.git
cd aethon

# 2. Sanal ortam oluşturun + etkinleştirin
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate

# 3. AETHON'u (düzenlenebilir) tüm isteğe bağlı özelliklerle kurun
pip install -e ".[all]"
#   yalın alternatif — yalnızca çekirdek, ekstraları sonra ekleyin:  pip install -e .

# 4. Doğrulayın
aethon --version                       # → aethon, version 0.2.0
```

:::tip `aethon`'un her yerde kullanılabilir olmasını mı istiyorsunuz (geliştirici kurulumu)?
venv yerine **pipx** kullanın: klonlanmış klasörden `pipx install -e .` çalıştırmak
PATH'inize izole bir `aethon` koyar ve kaynaktaki düzenlemeler bir sonraki çalıştırmada
geçerli olur — yeniden kurulum gerekmez.
:::

## Yol B — pip ile kur (hızlı; codex-proxy yok)

```bash
pip install "aethon-ai[all]"           # ya da yalnızca: pip install aethon-ai  (yalnızca çekirdek)
aethon --version
```

**Çekirdek kurulum, her giriş noktasını tek pakette getirir**: CLI + WebChat +
pano + Telegram (`aiogram`) + Discord (`discord.py`) + Slack (`slack-bolt`) +
bellek (`aiosqlite`) + SOP'ler (`strands-agents-sops`) + zamanlayıcı (`apscheduler`),
ayrıca Strands çekirdeği ve varsayılan OpenAI sağlayıcısı. **`[all]`**, yetenek
araçlarını ekler (web/GitHub/JSON-RPC/notify, macOS, LSP, dinamik araçlar,
bilgisayar). **`codex-proxy` pip paketinde yer almaz** — istiyorsanız klonlayın (Yol A).

:::info Paket adları
PyPI dağıtımı **`aethon-ai`**'dir (sade `aethon` adı alınmıştı), ancak içe
aktarılabilir paket ve CLI komutu her ikisi de **`aethon`**'dur. En güncel `main`'i
`pip install "git+https://github.com/mertozbas/aethon.git"` ile takip edin.
:::

## Bir model arka ucu yapılandırın

Rehberli sihirbazı çalıştırın — sağlayıcınızı sorar ve `~/.aethon/config.yaml`'ı yazar:

```bash
aethon init
```

Ardından size uyan yolu seçin (tam yapılandırma + codex-proxy adımları
**[Model Arka Uçları](./model-backends.md)** sayfasındadır):

- **OpenAI API anahtarı** — `sk-…` anahtarınızı yapıştırın. En basiti, anında çalışır.
- **codex-proxy aracılığıyla ChatGPT Pro** — AETHON'u API kredisi yerine ChatGPT planınızdan çalıştırın. Paketle gelen proxy'yi kendi terminalinde başlatın:
  ```bash
  cd codex-proxy && npm install && cp .env.example .env && npm run dev   # :8080'i sunar
  ```
  ardından AETHON'u `http://127.0.0.1:8080/v1` adresine yönlendirin.
- **Ollama (tamamen yerel)** — anahtar yok; `ollama` ekstrasını kurun ve yerel bir model çalıştırın.
- **OpenAI uyumlu herhangi bir uç nokta** — vLLM / LM Studio / LocalAI: `host`'u onun base URL'sine yönlendirin.

`aethon init`'i istediğiniz zaman yeniden çalıştırabilir ya da `~/.aethon/config.yaml`'ı elle düzenleyebilirsiniz.

## İlk çalıştırma + doğrulama

```bash
aethon doctor      # sağlayıcıyı/modeli + bellek hazırlığını kontrol eder
aethon start       # gateway'i + etkin her kanalı başlatır
```

Ardından şunları açın:

- **WebChat** → http://127.0.0.1:18790
- **Pano** → http://127.0.0.1:18790/dashboard  (oturumlar, Özellikler, kayıtlar, canlı şirket, loglar, …)
- **CLI** → `aethon start`'ı çalıştırdığınız terminale doğrudan yazın (çıkmak için `exit`).

:::warning codex-proxy mı kullanıyorsunuz?
AETHON açık olduğu sürece onun `npm run dev`'ini ayrı bir terminalde çalışır halde
tutun — kapalıysa, sohbet istekleri bağlantı hatasıyla başarısız olur.
:::

## İsteğe bağlı ekstralar

Bir ekstrayı `pip install "aethon-ai[ollama]"` ile (ya da bir klondan
`pip install -e ".[ollama]"` ile) isteyin. Bunları birleştirin, ör. `".[ollama,lsp,computer]"`.

| Ekstra | Kurulum | Eklediği | Amaç |
|-------|---------|------|---------|
| `anthropic` | `pip install "aethon-ai[anthropic]"` | `anthropic>=0.40.0` | `anthropic` sağlayıcısı (Anthropic API anahtarıyla Claude). |
| `ollama` | `pip install "aethon-ai[ollama]"` | `ollama>=0.3.0` | Yerel çıkarım sağlayıcısı (modelleri tamamen çevrimdışı çalıştırın). |
| `whatsapp` | `pip install "aethon-ai[whatsapp]"` | `neonize>=0.3.0` | WhatsApp kanalı (**deneysel**). |
| `mcp` | `pip install "aethon-ai[mcp]"` | `mcp>=1.0.0` | MCP sunucu desteği (`aethon mcp` + harici MCP araçları). |
| `scraper` | `pip install "aethon-ai[scraper]"` | `beautifulsoup4>=4.9.0` | `scraper` aracı (HTML/XML ayrıştırma). |
| `github` | `pip install "aethon-ai[github]"` | `colorama>=0.4.0` | `use_github` için renkli çıktı. |
| `jsonrpc` | `pip install "aethon-ai[jsonrpc]"` | `websockets>=12.0` | `jsonrpc` için WebSocket aktarımı. |
| `macos` | `pip install "aethon-ai[macos]"` | `html2text`, `mistune` | `apple_notes` için daha zengin Markdown (use_mac fazladan bir şey gerektirmez). |
| `lsp` | `pip install "aethon-ai[lsp]"` | `pyright>=1.1.0` | `lsp` aracı için Python LSP (diğer diller: sunucularını kurun). |
| `computer` | `pip install "aethon-ai[computer]"` | `pyautogui>=0.9.53` | `use_computer` (ekran/fare/klavye). |
| `launcher-macos` | `pip install "aethon-ai[launcher-macos]"` | `rumps>=0.4.0` | macOS menü çubuğu başlatıcısı (`aethon-menubar`). |
| `all` | `pip install "aethon-ai[all]"` | yukarıdaki özellik ekstraları | Özellik ekstralarını paketler. |
| `dev` | `pip install "aethon-ai[dev]"` | `pytest`, `pytest-asyncio`, `httpx` | Test/geliştirme araçları. |

## Güncelleme ve kaldırma

```bash
# Güncelleme — Yol A (klon):
cd aethon && git pull && pip install -e ".[all]"     # düzenlenebilir kurulum çoğu değişikliği otomatik alır
# Güncelleme — Yol B (pip):
pip install -U aethon-ai

# Kaldırma (~/.aethon içindeki verileriniz dokunulmadan kalır):
pip uninstall aethon-ai        # ya da: pipx uninstall aethon-ai
# Temiz bir başlangıç isterseniz verilerinizi de kaldırın:
rm -rf ~/.aethon
```

:::note Bir konteynerde mi çalıştırıyorsunuz?
Headless imaj, Compose ve yerel-Ollama profili için **[Docker rehberi](./docker.md)**
sayfasına bakın.
:::
