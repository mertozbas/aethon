---
id: configuration
title: Configuration
sidebar_label: Configuration
---

# Configuration

- **File location:** `~/.aethon/config.yaml` (override with `--config / -c` on any command).
- **Format:** YAML, validated with Pydantic. A **missing or empty file produces a fully-defaulted config** — every section falls back to its defaults.
- **Writing:** the wizard and tooling write YAML with `sort_keys=False` and `allow_unicode=True`, creating parent directories as needed.

:::tip
This page is the conceptual guide. For an exhaustive field-by-field table of every
config section, see the **[Configuration Reference](../reference/configuration.md)**.
:::

## Let the wizard do it

Most people never hand-edit the file. Run:

```bash
aethon init     # writes ~/.aethon/config.yaml
aethon doctor   # verifies provider/model + memory
```

`aethon init` walks a provider menu (**openai / anthropic / ollama**), configures
messaging bots, and (for Ollama embeddings) offers to install Ollama and pull the
embedding model. Use `--config / -c` to choose a path and `--force` to overwrite an
existing config without asking.

## `${ENV_VAR}` resolution

A string value is treated as an environment-variable reference **only if it starts
with `${` and ends with `}`** (whole-string only — no partial or interpolated
substitution). The inner name is looked up via `os.environ`. **A missing env var
resolves to an empty string `""`**, not an error. Resolution recurses into dicts and
lists; ints, bools, floats, and `None` pass through unchanged.

```yaml
channels:
  telegram:
    enabled: true
    token: ${TELEGRAM_BOT_TOKEN}   # actual secret supplied via the environment
```

:::note
Keep secrets in files like `~/.aethon/credentials/telegram.env` and export them into
the environment, rather than committing them into the config.
:::

## A minimal config

The smallest useful config just selects a provider and a key:

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}
```

Everything else (channels, memory, multi-agent, SOPs, scheduler, dashboard,
webhook, telemetry…) falls back to sensible defaults. Turn things on as you need
them — see the **[Configuration Reference](../reference/configuration.md)** for the
full set of sections and defaults.

## Capabilities & runtime features (opt-in)

The newer capability blocks are **off by default** unless noted. Powerful or
host-affecting features stay disabled until you opt in, and the security & approval
hooks gate the rest. (Browse live status in the dashboard's **Features** panel.)

```yaml
# Vendored utility tools (scraper/github/jsonrpc/notify default ON; computer OFF).
capabilities:
  scraper:  { enabled: true }
  github:   { enabled: true }      # use_github (reads $GITHUB_TOKEN)
  jsonrpc:  { enabled: true }
  notify:   { enabled: true, method: auto }
  computer: { enabled: false, require_approval: true }   # ⚠ screen/mouse/keyboard; needs [computer] + macOS perms

# macOS native tools (Darwin-only). Messages & Keychain are explicit opt-in.
macos:
  enabled: true
  enable_calendar: true
  enable_reminders: true
  enable_mail: true
  enable_notes: true
  enable_shortcuts: true
  enable_messages: false           # ⚠ can send iMessage/SMS as you
  enable_keychain: false           # ⚠ can read/write the Keychain
  actions_requiring_approval: ["mail.send", "messages.send", "keychain.set"]

lsp:                               # needs [lsp] (pyright) / language servers on PATH
  enabled: false
  auto_diagnostics: false          # append diagnostics after file-modifying tools

runtime_tools:                     # manage_tools (sandboxed dynamic tool loading)
  enabled: false
  allow_create: false              # create/fetch (subprocess sandbox validates first)
  allow_install: false             # add/reload (auto-install missing packages)

session_recorder:                  # timeline + snapshots → ZIP, replay in the dashboard
  enabled: false
  max_events: 10000

ambient:                           # proactive / autonomous idle-time work
  enabled: false
  auto_start: false

prompt:                            # system-prompt awareness layers
  include_environment: true
  include_learnings: true
  include_recent_logs: true
  include_shell_history: false     # privacy
  include_self_awareness: false    # embeds key source files — heavy

performance:
  max_tool_output_chars: 12000     # cap a single tool result so it can't overflow the context (0 = off)

paths:
  recordings: "~/.aethon/recordings"
```

See **[Capabilities](../concepts/capabilities.md)** for what each of these unlocks.
