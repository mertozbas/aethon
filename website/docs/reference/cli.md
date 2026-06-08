---
id: cli
title: CLI Reference
sidebar_label: CLI Reference
---

# CLI Reference

```bash
aethon [--version] <command> [options]
```

| Command | Description | Options |
|---|---|---|
| `aethon init` | Set up AETHON (provider menu openai/anthropic/ollama, model, memory, messaging bots) and write the config file. | `--config, -c <path>` (default `~/.aethon/config.yaml`); `--force` (overwrite an existing config without asking). |
| `aethon doctor` | Diagnose the current configuration and provider availability (provider/model, provider check, memory). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon start` | Start AETHON (runs the setup wizard first if no config exists; launches the gateway and all enabled channels). | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon mcp` | Serve AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over stdio. Informational output goes to stderr. | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon --version` | Print `aethon, version 0.2.0` and exit. | — |

Also installed with the `launcher-macos` extra: **`aethon-menubar`** — a macOS
menu-bar launcher (Start/Stop server, open WebChat, settings).
