---
id: cli
title: Interactive CLI
sidebar_label: Interactive CLI
---

# Interactive CLI

When you run `aethon start`, the console prints a status block: the provider and
model, the WebChat URL (`http://127.0.0.1:18790`), the memory/multi-agent/SOP/
scheduler/telemetry status, and (when enabled) the dashboard and webhook URLs and the
list of active channels. Then the gateway starts.

The CLI channel is enabled by default. After `aethon start`, type at the `you > `
prompt. Responses render as Markdown. Input history is saved to `~/.aethon/cli_history`.
Exit with `exit`, `quit`, `q`, or Ctrl-C / EOF.

```
you > what's on my plate today?
you > /code-assist refactor the auth module
you > exit
```

A message that starts with `/` is treated as an **SOP** command — see
**[SOPs](../concepts/sops.md)**. Everything else is a normal chat turn handled by the
orchestrator agent (which may delegate to specialists or call tools).
