---
id: multi-agent
title: Multi-agent specialists & delegation
sidebar_label: Multi-agent specialists
---

# Multi-agent specialists & delegation (`ask_*`)

A main orchestrator agent can delegate complex work to four specialists (all share the
runtime's model):

| id | name | focus | tools |
|----|------|-------|-------|
| `coder` | Coder | writing code, testing, debugging, refactoring (TDD) | `file_read, file_write, editor, shell, python_repl, think` |
| `researcher` | Researcher | web research, reading docs, gathering info (cites sources) | `http_request, file_read, think, current_time` |
| `analyst` | Analyst | data analysis, calculations, charts, reports | `python_repl, calculator, file_read, file_write, think` |
| `planner` | Planner | breaking complex tasks into concrete steps, prioritization | `file_read, file_write, think` |

Delegation tools: `ask_coder(task)`, `ask_researcher(query)`, `ask_analyst(data_task)`,
`ask_planner(planning_task)`. The orchestrator is instructed to handle simple tasks
itself and delegate complex ones.

```yaml
multi_agent:
  enabled: true
  max_handoffs: 10
  max_iterations: 10
  execution_timeout: 300.0   # seconds
  node_timeout: 120.0        # seconds
```

## Team modes (internal)

Beyond `ask_*`, two team modes exist internally:

- a **collaborative** mode (a Strands `Swarm` with handoffs, governed by
  `multi_agent.max_handoffs / max_iterations / execution_timeout / node_timeout`), and
- a **pipeline** mode (a deterministic `GraphBuilder` sequence; default pipeline
  `["planner", "researcher", "coder"]`).

:::info Roadmap
Swarm/Graph team & pipeline orchestration exists internally but isn't yet wired into
the runtime as a command/tool — see the **[Roadmap](../project/roadmap.md)**.
:::
