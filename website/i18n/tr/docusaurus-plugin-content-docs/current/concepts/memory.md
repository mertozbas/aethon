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

```yaml
memory:
  enabled: true
  embedding_provider: ollama        # or: openai
  embedding_model: nomic-embed-text
  embedding_api_key: ""             # needed for the openai provider
  db_path: ~/.aethon/memory.sqlite
```

:::note Bellek varsayılan olarak Ollama gerektirir
Varsayılan `ollama` gömme sağlayıcısıyla `ollama pull nomic-embed-text` komutunu
çalıştırın ve Ollama'yı çalışır halde tutun — ya da `embedding_provider: openai`
seçeneğine geçin ya da belleği devre dışı bırakın. Bkz. **[Sorun giderme](../operations/troubleshooting.md)**.
:::
