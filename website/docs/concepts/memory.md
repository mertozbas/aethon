---
id: memory
title: Memory (vector + embeddings)
sidebar_label: Memory
---

# Memory (vector + embeddings)

Long-term memory is a **SQLite vector store** with **provider embeddings** and
**cosine-similarity** search (a brute-force full scan; no ANN index). Storage lives at
`~/.aethon/memory.sqlite` by default.

- **Ollama embeddings (default):** uses `config.model.host` (default
  `http://localhost:11434`) and model `nomic-embed-text`. Requires Ollama running with
  that model pulled.
- **OpenAI embeddings:** set `memory.embedding_provider: openai` and
  `memory.embedding_api_key`.

The assistant manages memory with the `manage_memory` tool — actions `store`,
`search`, `list`, and `forget`, with categories like `preferences`, `projects`,
`decisions`, `learnings`. The **memory guard** hook keeps secrets out of long-term
memory.

```yaml
memory:
  enabled: true
  embedding_provider: ollama        # or: openai
  embedding_model: nomic-embed-text
  embedding_api_key: ""             # needed for the openai provider
  db_path: ~/.aethon/memory.sqlite
```

:::note Memory needs Ollama by default
With the default `ollama` embedding provider, run `ollama pull nomic-embed-text` and
keep Ollama running — or switch to `embedding_provider: openai`, or disable memory.
See **[Troubleshooting](../operations/troubleshooting.md)**.
:::
