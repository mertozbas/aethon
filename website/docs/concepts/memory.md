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

Each row records the embedding **model and dimension** it was stored with. Search
embeds the query and only scores rows whose dimension matches — rows embedded at a
different dimension are skipped (with a one-time warning) instead of being silently
truncated into a corrupt score. So switching the embedding model can't quietly
poison recall; re-embed the old rows to make them searchable again.

```yaml
memory:
  enabled: true
  embedding_provider: ollama        # or: openai
  embedding_model: nomic-embed-text
  embedding_api_key: ""             # needed for the openai provider
  db_path: ~/.aethon/memory.sqlite
```

## Automatic recall (opt-in)

By default the agent only sees long-term memory when it calls `manage_memory`
itself. Turn on **`memory.auto_recall`** (default **off**) and each incoming
message is embedded, the top matching memories are looked up, and they are injected
as a `## Recalled Memories` system-prompt layer — so relevant context surfaces
without the agent having to remember to search.

The recall layer sits in the volatile tail of the prompt, so it only re-sends (and
only changes the cached prefix) when the recalled set actually changes. Recalled
memories are treated as untrusted reference data, not instructions.

```yaml
memory:
  auto_recall: false        # opt-in; default off
  recall_top_k: 3           # how many memories to recall per message
  recall_min_score: 0.0     # only inject matches at/above this similarity
  recall_max_chars: 1500    # cap the size of the recall layer
```

:::note Memory needs Ollama by default
With the default `ollama` embedding provider, run `ollama pull nomic-embed-text` and
keep Ollama running — or switch to `embedding_provider: openai`, or disable memory.
See **[Troubleshooting](../operations/troubleshooting.md)**.
:::
