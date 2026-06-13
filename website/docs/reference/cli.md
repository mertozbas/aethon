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
| `aethon doctor` | Diagnose the current configuration and provider availability (provider/model, provider check, memory), plus disk-usage/retention, unknown config keys, path permissions, and secrets-hygiene warnings. | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon start` | Start AETHON (runs the setup wizard first if no config exists; launches the gateway and all enabled channels). Refuses a non-loopback bind without `dashboard.auth_token` unless `--insecure-bind` is passed. | `--config, -c <path>` (default `~/.aethon/config.yaml`); `--insecure-bind` (allow a non-loopback bind without `dashboard.auth_token` — only behind your own authenticating reverse proxy). |
| `aethon backup` | Back up `~/.aethon` to a live-safe `.tar.gz` (handles the SQLite store safely; skips `logs/`). | `--output, -o <path>` (default `~/.aethon-backup-<timestamp>.tar.gz`). |
| `aethon service install` | Install a run-at-boot service: a launchd agent on macOS, a systemd **user** unit on Linux. Prints the enable command. | — |
| `aethon mcp` | Serve AETHON's whole toolset to MCP clients (e.g. Claude Desktop) over stdio. Informational output goes to stderr. | `--config, -c <path>` (default `~/.aethon/config.yaml`). |
| `aethon --version` | Print `aethon, version <package version>` and exit. | — |

Also installed with the `launcher-macos` extra: **`aethon-menubar`** — a macOS
menu-bar launcher (Start/Stop server, open WebChat, settings).
