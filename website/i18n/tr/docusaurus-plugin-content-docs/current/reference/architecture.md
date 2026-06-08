---
id: architecture
title: Mimari
sidebar_label: Mimari
---

# Mimari

AETHON, kontrol panelini ve webhook yönlendiricilerini de barındıran tek bir
FastAPI/uvicorn sunucusuna (WebChat adaptörünün sahip olduğu) sahip bir Strands-Agents
uygulamasıdır; böylece her şey tek bir ana makine/portu paylaşır. Bir **gateway**, etkin
**kanal adaptörlerini** örnekler ve gelen mesajları **ajan çalışma zamanına (agent runtime)**
yönlendirir; bu çalışma zamanı çalışma alanı dosyalarından bir sistem istemi oluşturur,
**vektör belleğini** tutar, **uzman fabrikasını (specialist factory)** ve **SOP çalıştırıcısını**
bağlar ve **araçları** açığa çıkarır. Kesişen **hook'lar** telemetri, onay ve bellek korumasını
sağlar. İsteğe bağlı **MCP** sunucuları araç setini genişletir.

```
            ┌──────────────────────────────────────────────┐
            │                  Gateway                      │
            │  (starts only the enabled channel adapters)   │
            └──────────────────────────────────────────────┘
              │        │        │        │         │
            CLI     WebChat   Telegram  Discord   Slack ...
              │        │ (FastAPI/uvicorn: WebChat + dashboard + webhooks)
              ▼        ▼
            ┌──────────────────────────────────────────────┐
            │               Agent Runtime                   │
            │  system prompt ← SOUL/TOOLS/CONTEXT + layers  │
            │  ┌────────────┐  ┌──────────┐  ┌───────────┐  │
            │  │ Specialist │  │  Vector  │  │   SOP     │  │
            │  │  factory   │  │  memory  │  │  runner   │  │
            │  └────────────┘  └──────────┘  └───────────┘  │
            │         tools  ·  hooks (telemetry/approval/   │
            │                    memory guard)  ·  MCP       │
            └──────────────────────────────────────────────┘
```

## Katmanlar

- **Kanallar** — her giriş noktası için adaptörler (CLI, WebChat, Telegram, Discord, Slack, WhatsApp). Gateway yalnızca etkin olanları başlatır ve biri başlatılamazsa çalışmaya devam eder.
- **Çalışma zamanı (Runtime)** — sistem istemini çalışma alanı persona dosyalarından (artı isteğe bağlı ortam/öğrenimler/günlükler katmanlarından) oluşturur, orkestratör ajana sahiptir ve araç setini açığa çıkarır.
- **Uzmanlar** — `ask_*` devretme araçları aracılığıyla erişilen Coder / Researcher / Analyst / Planner alt ajanları.
- **Bellek** — sağlayıcı gömmeleri (embeddings) ve kosinüs benzerliği aramasına sahip bir SQLite vektör deposu.
- **SOP'lar** — yerleşik ve özel, eğik çizgiyle çağrılan iş akışları.
- **Hook'lar** — telemetri, onay kapısı ve bellek koruması araç çağrılarını sarmalar.
- **MCP** — isteğe bağlı harici MCP sunucuları araç setini genişletir; `aethon mcp`, AETHON'un kendi araçlarını MCP istemcilerine sunar.

## Daha derin referans

Depo, [`docs/`](https://github.com/mertozbas/aethon/tree/main/docs) altında tam tasarım
belgeleri içerir:

- [`docs/product/ARCHITECTURE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/ARCHITECTURE.md) — sistem mimarisi, veri akışları, bileşen ilişkileri.
- [`docs/product/PRODUCT.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/PRODUCT.md) — ürüne genel bakış.
- [`docs/product/API-REFERENCE.md`](https://github.com/mertozbas/aethon/blob/main/docs/product/API-REFERENCE.md) — HTTP/WebSocket API referansı.
- [`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md) — güvenlik modeli ve tehdit analizi.
- [`docs/development/ROADMAP.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/ROADMAP.md) — yol haritası.
