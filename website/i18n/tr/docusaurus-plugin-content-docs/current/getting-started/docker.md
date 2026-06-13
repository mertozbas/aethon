---
id: docker
title: Docker
sidebar_label: Docker
---

# Docker ile kurulum

İmaj **headless**'tir (web arayüzü + pano + webhook + mesajlaşma botları;
etkileşimli CLI bir konteyner içinde devre dışıdır). Bir sağlayıcıyı seedlenmiş
yapılandırma ya da ortam üzerinden sağlayın — varsayılan olarak yapılandırma,
`OPENAI_API_KEY` ile `provider: openai` kullanır (ya da `model.host`'u konteynerden
erişilebilir, OpenAI uyumlu bir base URL'ye yönlendirin).

:::warning Konteynerde bir pano token'ı ZORUNLUDUR
Konteyner, WebChat'i her zaman `0.0.0.0` adresine bağlar (port eşlemesinin ona
ulaşabilmesi için) ve AETHON, **loopback dışı bir bağlamada bir kimlik doğrulama
token'ı olmadan başlamayı reddeder**. Her zaman `AETHON_DASHBOARD_TOKEN` geçirin
(yeterince uzun herhangi bir gizli değer — ör. `$(openssl rand -hex 16)`). Kendi
kimlik doğrulayan ters proxy'nizin arkasında, bunun yerine komutu
`aethon start --insecure-bind` ile geçersiz kılabilirsiniz.
:::

## Docker Compose (önerilen)

```bash
AETHON_DASHBOARD_TOKEN=$(openssl rand -hex 16) \
OPENAI_API_KEY=sk-... \
docker compose up --build
# ardından http://127.0.0.1:18790/dashboard?token=YOUR_TOKEN adresini açın
# (/ws/chat'teki düz WebChat de token + izin verilen bir Origin gerektirir)
```

## Düz `docker run`

```bash
docker build -t aethon .
docker run -p 18790:18790 \
  -e AETHON_DASHBOARD_TOKEN=$(openssl rand -hex 16) \
  -e OPENAI_API_KEY=sk-... \
  aethon
```

## Build sırasında Ollama istemcisini pakete dahil etme

Yerel çıkarım yolu için:

```bash
docker compose build --build-arg EXTRAS=ollama
# ya da: docker build --build-arg EXTRAS=ollama -t aethon .
```

## Compose `local` profiliyle tamamen yerel çıkarım

`11434` portunda `aethon-ollama` adında bir `ollama/ollama` servisi çalıştırır:

```bash
docker compose --profile local up --build
# Ardından, veri biriminin config.yaml'ında şunu ayarlayın:
#   model.provider: ollama
#   model.host: http://ollama:11434
# (ve Ollama istemcisinin olması için imajı EXTRAS=ollama ile build edin)
```

## Bilinmeye değer Docker gerçekleri

- **Temel imaj:** çok aşamalı `python:3.12-slim` (builder + runtime), root olmayan `aethon` kullanıcısı (uid 10001) olarak `WORKDIR /home/aethon` altında çalışır.
- **Durum/yapılandırma**, `/home/aethon/.aethon` altına bağlanan **`aethon-data`** adlı birimde yer alır. Seedlenmiş `docker/config.docker.yaml`, `/home/aethon/.aethon/config.yaml`'a **yalnızca birim boş olduğunda** kopyalanır — bağlanmış bir yapılandırma/birim önceliklidir.
- **Bağlama:** WebChat, konteyner içinde **`0.0.0.0:18790`** adresine bağlanır; böylece `18790:18790` port eşlemesi ona ulaşır.
- **Sağlayıcı:** seedlenmiş yapılandırma varsayılan olarak ortamdan `OPENAI_API_KEY` okuyan `provider: openai`'dir; bunu `-e OPENAI_API_KEY=…` ile (ya da Compose'ta `environment:` ile) geçirin, ya da `model.host`'u OpenAI uyumlu bir base URL'ye ayarlayın.
- **Bellek imajda varsayılan olarak devre dışıdır** (bir Ollama gömme arka ucuna ihtiyaç duyar).
- **Healthcheck**, konteyner içinde `http://127.0.0.1:18790/health` adresini yoklar.
- **Diğer sağlayıcılar:** yapılandırmada `provider`'ı değiştirin ve eşleşen kimlik bilgilerini sağlayın (ör. `anthropic` için `ANTHROPIC_API_KEY`).
- **`AETHON_DASHBOARD_TOKEN` imaj için ZORUNLUDUR** — konteyner her zaman `0.0.0.0` adresine bağlanır ve AETHON, loopback dışı bir bağlamada bu olmadan başlamayı reddeder. Kendi kimlik doğrulayan ters proxy'nizin arkasında, bir token ayarlamak yerine komutu `aethon start --insecure-bind` ile geçersiz kılabilirsiniz.
- **Webhook'lar konteynerde kapalı (fail-closed) davranır:** `AETHON_WEBHOOK_SECRET` ayarlanmamışsa `/webhook/*` yolları yalnızca **kaydedilmez** (geri kalanı çalışmaya devam eder). Onları etkinleştirmek için bunu ayarlayın — çağıranlar bunun ardından istek gövdesini `X-Aethon-Signature` başlığında HMAC-SHA256 ile imzalar.

:::warning Docker sağlayıcınıza ulaşamıyor mu?
`model.host`, ana makinedeki bir servise (ör. yerel bir OpenAI uyumlu sunucu ya da
Ollama) işaret ediyorsa, konteyner içinden `http://host.docker.internal:<port>`
kullanın ve `host.docker.internal`'ın çözümlendiğinden emin olun — Compose,
`extra_hosts: host.docker.internal:host-gateway` ayarlar; düz `docker run` için
`--add-host host.docker.internal:host-gateway` ekleyin. Resmi OpenAI API'si için
yalnızca `OPENAI_API_KEY`'i konteynere geçirin.
:::
