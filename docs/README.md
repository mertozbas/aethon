# AETHON — Dokumantasyon

> Kisisel AI Asistan — Yerel LLM, cok kanal, cok agent, tam kontrol.

---

## Dokuman Yapisi

### Urun Dokumanlari (`product/`)

| Dokuman | Aciklama |
|---------|----------|
| [PRODUCT.md](product/PRODUCT.md) | Urun tanimi, ozellikler, mimari bakis |
| [GETTING-STARTED.md](product/GETTING-STARTED.md) | Kurulum ve hizli baslangic rehberi |
| [CONFIGURATION.md](product/CONFIGURATION.md) | Tum config ayarlarinin referansi |
| [API-REFERENCE.md](product/API-REFERENCE.md) | HTTP endpoint, WebSocket, webhook, tool referansi |
| [ARCHITECTURE.md](product/ARCHITECTURE.md) | Teknik mimari, veri akislari, bilesken iliskileri |

### Gelistirme Dokumanlari (`development/`)

| Dokuman | Aciklama |
|---------|----------|
| [PHASE-1-CORE.md](development/PHASE-1-CORE.md) | Faz 1 — Cekirdek altyapi tasarim dokumani |
| [PHASE-2-CHANNELS.md](development/PHASE-2-CHANNELS.md) | Faz 2 — Kanal entegrasyonlari tasarimi |
| [PHASE-3-MULTIAGENT.md](development/PHASE-3-MULTIAGENT.md) | Faz 3 — Multi-agent orkestrasyon tasarimi |
| [PHASE-4-POLISH.md](development/PHASE-4-POLISH.md) | Faz 4 — Cilalama ve ileri ozellikler tasarimi |
| [ROADMAP.md](development/ROADMAP.md) | Proje yol haritasi |
| [SECURITY.md](development/SECURITY.md) | Guvenlik modeli ve tehdit analizi |

### Kontrol Listeleri (`checklists/`)

| Dokuman | Aciklama |
|---------|----------|
| [PHASE-1-CHECKLIST.md](checklists/PHASE-1-CHECKLIST.md) | Faz 1 tamamlanma kontrol listesi |
| [PHASE-2-CHECKLIST.md](checklists/PHASE-2-CHECKLIST.md) | Faz 2 tamamlanma kontrol listesi |
| [PHASE-3-CHECKLIST.md](checklists/PHASE-3-CHECKLIST.md) | Faz 3 tamamlanma kontrol listesi |
| [PHASE-4-CHECKLIST.md](checklists/PHASE-4-CHECKLIST.md) | Faz 4 tamamlanma kontrol listesi |

### Referanslar (`references/`)

| Dokuman | Aciklama |
|---------|----------|
| [strands-agents-reference.md](references/strands-agents-reference.md) | Strands Agents SDK API referansi |
| [qwen3-coder-next-reference.md](references/qwen3-coder-next-reference.md) | Qwen3-Coder-Next model ozellikleri |

---

## Hizli Erisim

**Yeni kullanicilar icin:** [Baslangic Rehberi](product/GETTING-STARTED.md) ile baslayin.

**Yapilandirma icin:** [Config Referansi](product/CONFIGURATION.md) dosyasinda tum ayarlar aciklanmistir.

**API entegrasyonu icin:** [API Referansi](product/API-REFERENCE.md) dosyasinda tum endpoint'ler, webhook'lar ve tool'lar belgelenmistir.

**Teknik detaylar icin:** [Mimari Dokumani](product/ARCHITECTURE.md) katmanli mimariyi, veri akislarini ve bilesken iliskilerini aciklar.

---

## Proje Durumu

| Faz | Durum | Test |
|-----|-------|------|
| Faz 1 — Cekirdek | Tamamlandi | 64 test |
| Faz 2 — Kanallar | Tamamlandi | 120 test |
| Faz 3 — Multi-Agent | Tamamlandi | 178 test |
| Faz 4 — Cilalama | Tamamlandi | 294 test |

Toplam: **294 test**, hepsi gecen.
