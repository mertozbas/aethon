---
id: workspace
title: Workspace files (SOUL / TOOLS / CONTEXT)
sidebar_label: Workspace files
---

# Workspace files (SOUL / TOOLS / CONTEXT)

On `aethon start`, AETHON ensures the workspace at `~/.aethon/workspace` exists and
seeds three Markdown files (each written only if it doesn't already exist — your edits
are preserved):

- **`SOUL.md`** — the assistant's persona/system identity. Sections: **Identity** (be
  pragmatic and direct; own mistakes; say when you don't know), **Communication**
  (speaks English and Turkish, replies in the user's language; short focused answers;
  Markdown formatting), **Decision Making** (do simple tasks directly; propose a plan
  for complex tasks; pick the simplest approach).
- **`TOOLS.md`** — your preferences and capabilities. Sections: **Code Standards**
  (Python 3.10+, type hints, f-strings, asyncio + OOP, no needless comments, test
  against real data), **Expert Delegation** (`ask_coder`, `ask_researcher`,
  `ask_analyst`, `ask_planner`), **Memory** (save with `manage_memory`; categories
  preferences/projects/decisions/learnings; never store secrets), **Context** (keep
  `CONTEXT.md` current with `update_context`).
- **`CONTEXT.md`** — live working state, seeded with empty placeholders for **Active
  Project**, **Recent Decisions**, and **Notes**.

It also creates `<workspace>/sops`, the sessions directory, the logs directory, and
(if memory is enabled) the memory DB's parent directory.

:::tip
These files **are** the assistant's behavior. Edit `SOUL.md` to change its persona,
`TOOLS.md` to set your standards, and let it keep `CONTEXT.md` current via the
`update_context` tool.
:::
