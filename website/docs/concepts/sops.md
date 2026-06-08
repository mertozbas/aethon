---
id: sops
title: SOPs (Standard Operating Procedures)
sidebar_label: SOPs
---

# SOPs (Standard Operating Procedures)

SOPs are reusable workflows invoked with a slash command. **Built-ins:**

```
/code-assist        /pdd        /codebase-summary
```

(from the `strands-agents-sops` package; toggle with `sops.builtin_sops_enabled`, and
the whole subsystem with `sops.enabled`).

**Invoking:** a message that starts with `/` is treated as an SOP command; the first
token after `/` is the SOP name and the rest is your input. It only matches loaded SOPs.

## Authoring a custom SOP

Create a Markdown file at:

```
~/.aethon/workspace/sops/<name>.sop.md
```

The SOP name is the filename with `.sop.md` removed, so `weekly-report.sop.md` is
invoked as `/weekly-report`. A `## Overview` section is parsed for the SOP's
description (first 200 chars), shown in listings (the dashboard SOPs panel and
`/api/sops`). The agent's system prompt lists the available SOP slash-commands by name.
Custom SOPs are merged with built-ins.

```markdown
## Overview
Generate a concise weekly status report from recent commits and notes.

## Steps
1. Summarize recent activity.
2. Highlight blockers and decisions.
3. Output a Markdown report.
```

You can also create/edit/delete custom SOPs from the dashboard's SOPs panel (built-ins
can't be deleted).
