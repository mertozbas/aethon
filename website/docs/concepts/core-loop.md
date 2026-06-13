---
id: core-loop
title: The autonomous core loop
sidebar_label: Core loop
---

# The autonomous core loop

AETHON's core loop turns a unit of work into **intake → plan → execute →
deliver-with-proof**: a request is recognised as a project, planned into the task
ledger, worked toward completion by a bounded executor, and reported back with an
evidence-backed receipt. Every stitch is gated under `core_loop.*` and is **opt-in /
off by default** — ordinary chat is untouched until you enable it.

:::info Bounded by design
The executor is deliberately fenced in: an iteration cap, a re-checked spend ceiling,
and a per-task attempt limit keep an autonomous run from spinning. It also trusts the
**ledger**, never the agent's prose — a task counts as done only when it is marked done
with evidence.
:::

## 1. Intake — classify a unit of work (`core_loop.intake_enabled`)

When intake is on, an incoming message is classified as **chat** or **work** before the
normal turn runs. The classifier is a transparent, high-bar heuristic (no model call on
the hot path) and is biased toward chat — a question, a short message, or anything that
doesn't pair a build/creation verb with a project noun stays chat. You always have an
explicit override either way via `core_loop.intake_work_phrases` /
`intake_chat_phrases` (e.g. "treat this as a project" / "just a question").

A clear unit of work is opened as a planned project and acknowledged, instead of being
answered as a normal chat turn. Anything short of a confidently-opened project falls
through to ordinary processing, so chat is never hijacked. Intake needs the task ledger
and the planner available; otherwise it's a no-op.

## 2. Plan → ledger (`ask_planner`)

The planner specialist returns a **structured** plan, and `ask_planner` persists it
straight into the task ledger as a dependency-ordered project tree: a parent project
plus child tasks, each with a title, acceptance criteria, a priority
(`critical | high | medium | low`), and dependencies expressed as positions into the
plan. So the plan becomes a visible ledger diff the user (and the executor) can inspect,
rather than free text the agent has to re-interpret. A provider that can't force
structured output falls back to a free-text plan.

`core_loop.plan_approval` (default off) records that execution should wait for the user
to approve a freshly-planned project; the plan itself is always written to the ledger.

## 3. Execute — the bounded `ProjectExecutor` (`core_loop.executor_enabled`)

When the executor is on and a project is active, an [ambient](./capabilities.md) tick
runs the `ProjectExecutor` against it. Each iteration it picks the most-urgent task
whose dependencies are satisfied, drives one agent turn on it, and advances only when
the ledger shows progress. The run is bounded on every axis:

- **`executor_max_iterations`** (default 20) — a hard cap on task turns per project run.
- **`executor_max_task_attempts`** (default 3) — a task that makes no progress after
  this many turns is **dropped** (durably, so it leaves the queue for good — the counter
  lives in the ledger, surviving restarts and re-invocation).
- **`executor_stop_on_budget`** (default on) — the token spend ceiling is re-checked
  *between* tasks (the per-turn gate alone can't bound a multi-task run); the run halts
  when it's breached.

The run ends with a structured stop reason: `complete`, `partial` (some tasks dropped),
`blocked` (unsatisfiable dependencies), `cap` (iteration limit), or `budget`.

## 4. Pulse + proof-of-work receipt (`core_loop.pulse_enabled` / `receipt_enabled`)

While executing, AETHON sends progress **pulses** back to the channel the work was
requested from — one every `core_loop.pulse_every_n_tasks` newly-completed tasks
(default 3; silenceable with `pulse_enabled: false`).

When a run ends, `receipt_enabled` (default on) delivers an honest **proof-of-work
receipt**: each completed task is listed with the real evidence the ledger captured
(never a bare "done", never fabricated), and dropped tasks are shown as not completed.
This is the product's "done, here's the proof" payoff.

```yaml
core_loop:
  intake_enabled: false          # C1 — classify work vs chat
  executor_enabled: false        # C3 — run the bounded executor on an active project
  executor_max_iterations: 20
  executor_max_task_attempts: 3
  executor_stop_on_budget: true
  pulse_enabled: true            # C4 — progress pulses while executing
  pulse_every_n_tasks: 3
  receipt_enabled: true          # C4 — proof-of-work receipt when a run ends
  plan_approval: false           # record that execution awaits approval
```

See **[Multi-agent specialists](./multi-agent.md)** for the planner that produces the
plan, **[Agent tools](./tools.md)** for the `manage_tasks` ledger, and
**[Capabilities](./capabilities.md)** for the ambient loop that drives execution.
