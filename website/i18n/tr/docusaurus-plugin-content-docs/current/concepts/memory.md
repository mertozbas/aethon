---
id: memory
title: Bellek (vektör + gömme)
sidebar_label: Bellek
---

# Bellek (vektör + gömme)

Uzun süreli bellek, **sağlayıcı gömmeleri** ve **kosinüs benzerliği** araması kullanan
bir **SQLite vektör deposudur** (kaba kuvvetle tam tarama; ANN dizini yoktur). Depolama
varsayılan olarak `~/.aethon/memory.sqlite` konumunda bulunur.

- **Ollama gömmeleri (varsayılan):** `config.model.host` (varsayılan
  `http://localhost:11434`) ve `nomic-embed-text` modelini kullanır. Ollama'nın o model
  çekilmiş halde çalışıyor olmasını gerektirir.
- **OpenAI gömmeleri:** `memory.embedding_provider: openai` ve
  `memory.embedding_api_key` ayarlarını belirleyin.

Asistan belleği `manage_memory` aracıyla yönetir — `store`, `search`, `list` ve
`forget` eylemleri ve `preferences`, `projects`, `decisions`, `learnings` gibi
kategorilerle. **Bellek koruyucu (memory guard)** hook'u, gizli bilgilerin uzun süreli
bellekten uzak kalmasını sağlar.

Her satır, hangi gömme **modeli ve boyutuyla** depolandığını kaydeder. Arama, sorguyu
gömer ve yalnızca boyutu eşleşen satırları puanlar — farklı bir boyutla gömülmüş satırlar
sessizce bozuk bir puana kırpılmak yerine atlanır (tek seferlik bir uyarıyla). Böylece
gömme modelini değiştirmek hatırlamayı sessizce zehirleyemez; eski satırları yeniden
arama yapılabilir hâle getirmek için yeniden gömün.

```yaml
memory:
  enabled: true
  embedding_provider: ollama        # or: openai
  embedding_model: nomic-embed-text
  embedding_api_key: ""             # needed for the openai provider
  db_path: ~/.aethon/memory.sqlite
```

## Otomatik hatırlama (isteğe bağlı)

Varsayılan olarak ajan, uzun süreli belleği yalnızca kendisi `manage_memory` çağırdığında
görür. **`memory.auto_recall`** (varsayılan **kapalı**) açıldığında, gelen her mesaj
gömülür, en iyi eşleşen bellekler aranır ve bir `## Recalled Memories` sistem istemi
katmanı olarak enjekte edilir — böylece ilgili bağlam, ajanın arama yapmayı hatırlamasına
gerek kalmadan yüzeye çıkar.

Hatırlama katmanı, istemin değişken kuyruğunda yer alır; bu nedenle yalnızca hatırlanan
küme gerçekten değiştiğinde yeniden gönderilir (ve yalnızca o zaman önbelleğe alınmış öneki
değiştirir). Hatırlanan bellekler, talimat olarak değil, güvenilmeyen başvuru verisi olarak
ele alınır.

```yaml
memory:
  auto_recall: false        # isteğe bağlı; varsayılan kapalı
  recall_top_k: 3           # mesaj başına kaç bellek hatırlanacağı
  recall_min_score: 0.0     # yalnızca bu benzerlikte/üzerinde eşleşmeleri enjekte et
  recall_max_chars: 1500    # hatırlama katmanının boyutunu sınırla
```

:::note Bellek varsayılan olarak Ollama gerektirir
Varsayılan `ollama` gömme sağlayıcısıyla `ollama pull nomic-embed-text` komutunu
çalıştırın ve Ollama'yı çalışır halde tutun — ya da `embedding_provider: openai`
seçeneğine geçin ya da belleği devre dışı bırakın. Bkz. **[Sorun giderme](../operations/troubleshooting.md)**.
:::
