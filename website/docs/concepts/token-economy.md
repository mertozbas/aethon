---
id: token-economy
title: Token economy
sidebar_label: Token economy
---

# Token economy

A self-hosted assistant that runs continuously can quietly burn tokens. AETHON's
token-economy subsystem is a set of deliberate levers — measure spend, compact old
context, orient without re-reading, isolate bulky reads, and keep the prompt cache
warm. Each lever is **opt-in / off by default** unless noted.

## Budget metering + daily ceiling (`budget`)

Token usage is measured per turn. With `budget.daily_usd` set above `0`, turns are
warned as spend approaches the ceiling (`budget.warn_ratio`, default `0.8`) and
**blocked** once it is breached — including ambient and scheduler turns, which run
through the same path. `budget.pricing` overrides the built-in price table (USD per 1M
tokens). This is the real antidote to the "an API will burn hundreds of dollars" fear.

```yaml
budget:
  daily_usd: 0.0        # 0 = unlimited (measure only)
  warn_ratio: 0.8       # warn once spend crosses this fraction of the ceiling
  pricing: {}           # {model_substring: {input: x, output: y}} per 1M tokens
```

## History compaction (`session.compact_*`)

On a long-horizon session the old, large tool outputs in the model's input add up.
With `session.compact_enabled` on (default **off**), old, large tool results are
replaced with a compact marker so the conversation stays affordable. It compacts in
**batches** — and never touches the most recent turns — so it disturbs the provider
message cache rarely, not every turn.

```yaml
session:
  compact_enabled: false
  compact_keep_last_n_turns: 4    # never touch the most recent N turns
  compact_min_chars: 800          # only compact a result bigger than this
  compact_trigger_chars: 16000    # run a pass once this much old bulk piles up
```

## Repo map (`repo_map.enabled`)

When on (default **off**), files the agent reads are summarised — path → purpose,
symbols, content hash — in `workspace/REPO_MAP.json`, and a compact map is injected as
a `## Repo Map` prompt layer. So the next session is oriented without re-reading the
same files. The map is capped (newest `max_files`, files under `max_file_bytes`, and a
`max_snapshot_chars` prompt-layer size limit) and the layer is cache-safe.

```yaml
repo_map:
  enabled: false
  max_files: 100
  max_file_bytes: 200000
  max_snapshot_chars: 2000
```

## Scout — read many, return little (`ask_scout`)

The scout specialist reads/searches the sources you point it at and is instructed to
return **only** a concise conclusion. The raw material stays in the scout's context, not
the main agent's — so "read these files and tell me X" doesn't dump the files into your
turn. (Isolation is advisory — it relies on the scout following its brief, with the
tool-output cap as the structural backstop.) See
**[Multi-agent specialists](./multi-agent.md)**.

## Capability diet (`core_loop.capability_diet`)

Heavy, domain-specific tools carry large schemas that ride along on every turn. The
diet keeps an always-on core toolset and loads the heavy tools (`use_mac`,
`use_computer`, `use_github`, `apple_notes`, `scraper`, `jsonrpc`) into a session only
when its building message matches their keywords — decided once per session, not per
turn, so the prompt/tool cache stays warm. Off by default. See
**[Capabilities](./capabilities.md)**.

## Prompt-cache layering

The system prompt is built as a **stable prefix** plus a **volatile tail**. Content
that changes per turn (current context, recalled memories, the open-tasks snapshot, the
timestamp) lives in the tail, so an unchanged turn re-sends only the tail and keeps the
cached prefix warm. Volatile layers refresh only when their source actually changes, and
the per-turn log tail is deliberately kept out of the prompt so it can't make every turn
unique and defeat caching.
