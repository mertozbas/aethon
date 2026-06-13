---
id: faq
title: FAQ
sidebar_label: FAQ
---

# FAQ

### Do I need an API key?

For the default OpenAI provider, yes — supply `OPENAI_API_KEY` (or point `model.host`
at an OpenAI-compatible endpoint, where local servers often accept a placeholder key).
To run with **no key at all**, use the fully-local **Ollama** provider. API providers
like Anthropic also need their own key.

### Where does AETHON store my data?

Under `~/.aethon` — config (`config.yaml`), workspace (`workspace/`), sessions
(`sessions/`), logs (`logs/`), vector memory (`memory.sqlite`), and credentials
(`credentials/`).

### Is AETHON open source?

It's **source-available** under PolyForm Noncommercial 1.0.0 — free for noncommercial
use, but **not** OSI-approved open source (commercial use isn't permitted). See
**[License](../project/license.md)**.

### Can I run it fully offline / locally?

Yes. Install the `ollama` extra, set `provider: ollama`, and use Ollama embeddings for
memory. No cloud calls are required in that configuration.

### How do I expose the Web UI on my network?

Set `channels.webchat.host: 0.0.0.0` and **also** set `dashboard.auth_token`. Then
reach the dashboard with `?token=YOUR_TOKEN` to set the auth cookie.

### Which channels need extra installs?

Only **WhatsApp** (the `whatsapp` extra). CLI, WebChat, Telegram, Discord, and Slack
all ship in the core install.

### How do I add my own workflow?

Drop a `*.sop.md` file in `~/.aethon/workspace/sops/` (with an `## Overview` section)
and invoke it as `/<name>`. See **[SOPs](../concepts/sops.md)**.

### Will an API provider run up a huge bill?

Set `budget.daily_usd` to cap daily spend. Every turn's token usage is measured and
costed (override the built-in rate table with `budget.pricing`); turns are warned once
spend crosses `budget.warn_ratio` (default `0.8`) of the ceiling and **blocked** once it
is breached — which also halts ambient and scheduler turns. The default `0.0` means
unlimited (measure only). To avoid cloud spend entirely, run fully local with Ollama.

### Does the assistant remember things between sessions?

Yes, when memory is enabled. It stores embeddings in SQLite and retrieves them by
similarity. The memory guard prevents secrets from being saved. With
`memory.auto_recall` on (opt-in, off by default), each turn embeds the incoming message
and injects the top-matching long-term memories as a prompt layer, so relevant memories
surface without the agent calling the memory tool. Vector memory also records each row's
embedding model and dimension and refuses to mix dimensions, so changing the embedding
model can't silently corrupt similarity search.
