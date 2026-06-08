---
id: development
title: Geliştirme
sidebar_label: Geliştirme
---

# Geliştirme

```bash
git clone https://github.com/mertozbas/aethon.git
cd aethon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Testleri çalıştırma

`e2e` işaretçisi (marker) bir alt süreç başlatır ve bir sokete bağlanır; `ollama` işaretçisi çalışan bir
Ollama gerektirir.

```bash
pytest                       # tüm paket
pytest -q                    # sessiz
pytest -m "not e2e"          # uçtan uca başlatma testlerini atla
```

## Lint

CI'nin zorunlu kıldığı hata seviyesindeki (error-level) denetim:

```bash
ruff check --select E9,F63,F7,F82 aethon
```

## CI

`.github/workflows/ci.yml` (`CI` adıyla, `main` dalına push/PR üzerine) üç iş çalıştırır:

- `test` — Python 3.10 / 3.11 / 3.12 üzerinde matris; `pip install -e ".[dev]"`; hata seviyesi ruff lint; `pytest -q`.
- `build` — 3.12 üzerinde `python -m build` + `twine check dist/*`.
- `docker` — `aethon:ci` imajını oluşturur (push yok).

Katkılar aynı ticari olmayan koşullara tabidir;
[CONTRIBUTING.md](https://github.com/mertozbas/aethon/blob/main/CONTRIBUTING.md) dosyasına bakın.

## Dokümantasyon sitesi

Bu el kitabı, `website/` altında bir [Docusaurus](https://docusaurus.io) sitesidir. Üzerinde yerel olarak
çalışmak için:

```bash
cd website
npm install
npm start                    # sıcak yeniden yükleme (hot reload) ile geliştirme sunucusu
npm run build                # website/build içine üretim derlemesi
```

Çevrilmiş içerik `website/i18n/<locale>/` altında yer alır. Site, `main` dalından
`.github/workflows/docs.yml` aracılığıyla otomatik olarak GitHub Pages'e dağıtılır.
