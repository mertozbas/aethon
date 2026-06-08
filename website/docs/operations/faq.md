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

### Does the assistant remember things between sessions?

Yes, when memory is enabled. It stores embeddings in SQLite and retrieves them by
similarity. The memory guard prevents secrets from being saved.
