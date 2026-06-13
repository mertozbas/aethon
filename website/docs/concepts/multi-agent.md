---
id: multi-agent
title: Multi-agent specialists & delegation
sidebar_label: Multi-agent specialists
---

# Multi-agent specialists & delegation (`ask_*`)

A main orchestrator agent can delegate complex work to its built-in specialists (all
share the runtime's model):

| id | name | focus | tools |
|----|------|-------|-------|
| `coder` | Coder | writing code, testing, debugging, refactoring (TDD) | `file_read, file_write, editor, shell, python_repl, think` |
| `researcher` | Researcher | web research, reading docs, gathering info (cites sources) | `http_request, file_read, think, current_time` |
| `analyst` | Analyst | data analysis, calculations, charts, reports | `python_repl, calculator, file_read, file_write, think` |
| `planner` | Planner | breaking complex tasks into concrete, prioritized steps | `file_read, file_write, think` |
| `scout` | Scout | "read many, return little" investigation: reads/searches sources, returns only a concise conclusion | `file_read, shell, think` |

Delegation tools: `ask_coder(task)`, `ask_researcher(query)`, `ask_analyst(data_task)`,
`ask_planner(planning_task)`, `ask_scout(query)`, and the generic
`ask_specialist(specialist_name, task)` (reaches any specialist — built-in or custom —
by name). The orchestrator is instructed to handle simple tasks itself and delegate
complex ones.

`ask_scout` is the "read many, return little" tool: the scout reads/searches the
sources you point it at and returns only a concise conclusion, keeping raw dumps out
of the main agent's context (isolation is advisory — it relies on the scout following
its brief, with the tool-output cap as the structural backstop).

When the task ledger is wired (Phase 10), `ask_planner` no longer returns free text:
it persists a structured plan into the ledger as a dependency-ordered project tree
(parent project + child tasks with acceptance criteria, priorities, and dependencies)
and returns a summary, with a free-text plan as the fallback when the provider can't
produce structured output.

## Custom specialists (opt-in)

With **`core_loop.dynamic_specialists`** on (default **off**), the agent can define
its own specialists. `manage_specialists(action, name, system_prompt, tools)` creates,
lists, and removes custom specialists, which persist to `workspace/specialists/*.json`
across sessions; `ask_specialist(name, task)` then delegates to any of them by name.

- A specialist's tools must come from a fixed allowlist (`file_read`, `file_write`,
  `editor`, `shell`, `think`, `current_time`, `python_repl`, `http_request`,
  `calculator`), enforced both at creation and when loading from disk — a hand-edited
  JSON file can't smuggle in a tool that isn't allowed.
- The **powerful** tools (`shell`, `python_repl`, `file_write`, `editor`,
  `http_request`) are only granted when `core_loop.allow_powerful_specialists` is on;
  otherwise only the read-only/pure-compute subset is available.
- Creating a specialist is approval-gated, and custom specialists inherit the same
  security, sandbox, and hooks as the built-ins.

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
