"""Plan → ledger pipeline (Phase 10 C2).

The planner specialist returns a *structured* plan; ``persist_plan`` turns it
into a dependency-ordered project tree in the TaskLedger — so the plan becomes a
visible ledger diff the user (and the C3 executor) can inspect and approve,
rather than free text the agent has to re-interpret.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

logger = logging.getLogger("aethon.planning")


class PlanTask(BaseModel):
    """One step of a plan.

    ``depends_on`` uses **1-based positions** into the plan's own task list
    (e.g. ``["1", "2"]`` = "after the first and second steps") — local refs the
    pipeline maps to the real ledger ids once the tasks are created.
    """

    title: str = ""
    acceptance_criteria: str = ""
    priority: str = "medium"
    depends_on: list[str] = Field(default_factory=list)


class PlanSchema(BaseModel):
    """A structured plan: a project and its ordered child tasks."""

    project_title: str = ""
    tasks: list[PlanTask] = Field(default_factory=list)


def persist_plan(ledger, plan: PlanSchema, *, plan_approval: bool = False) -> dict | None:
    """Write a ``PlanSchema`` into the ledger as a parent project + child tasks
    with mapped dependencies. Returns ``{project_id, task_ids, summary}`` or
    ``None`` when the plan has no tasks (the caller then falls back to free text).

    Two passes so local refs always resolve: create every child first (assigning
    ids), then map each child's 1-based ``depends_on`` positions to the real ids
    and set them. A child whose dependencies don't validate (unknown ref / cycle)
    keeps its other fields — the plan still lands; only the bad edge is dropped
    (advisory, logged), never the whole plan.
    """
    tasks = list(plan.tasks or [])
    if not tasks:
        return None

    project = ledger.create(
        plan.project_title or "Proje",
        plan_origin="ask_planner",
        priority="high",
    )
    project_id = project["id"]

    # Pass 1 — create children without dependencies; record position → real id.
    pos_to_id: dict[str, str] = {}
    child_ids: list[str] = []
    for i, pt in enumerate(tasks, start=1):
        child = ledger.create(
            pt.title,
            acceptance_criteria=pt.acceptance_criteria,
            plan_origin=f"ask_planner:{project_id}",
            parent_id=project_id,
            priority=pt.priority,
        )
        pos_to_id[str(i)] = child["id"]
        child_ids.append(child["id"])

    # Pass 2 — map local refs to real ids and set validated dependencies. Each
    # edge is isolated: a validation problem OR an unexpected update() failure on
    # one child drops only that edge (logged) — the plan still lands whole, never
    # an orphaned half-plan that then falls back to free text (review fix).
    for pt, cid in zip(tasks, child_ids):
        if not pt.depends_on:
            continue
        real_deps = []
        for ref in pt.depends_on:
            ref = str(ref).strip()
            real_deps.append(pos_to_id.get(ref, ref))  # position → id, else as-is
        try:
            problems = ledger.dependency_problems(cid, real_deps)
            if problems:
                logger.warning(
                    "Dropping dependency on %s (%s) — plan still persisted.",
                    cid, "; ".join(problems),
                )
                continue
            ledger.update(cid, depends_on=real_deps)
        except Exception as e:
            logger.warning(
                "Failed to set dependencies on %s (%s: %s) — plan still persisted.",
                cid, type(e).__name__, e,
            )

    summary = _summarize(ledger, project_id, child_ids, plan_approval)
    return {"project_id": project_id, "task_ids": child_ids, "summary": summary}


def _summarize(ledger, project_id: str, child_ids: list[str], plan_approval: bool) -> str:
    """A compact, user-facing (TR) rendering of the persisted plan."""
    project = ledger.get(project_id) or {}
    lines = [f"Plan kaydedildi — proje [{project_id}] {project.get('title', '')}".strip()]
    for cid in child_ids:
        task = ledger.get(cid) or {}
        line = f"- [{cid}] ({task.get('priority', 'medium')}) {task.get('title', '')}"
        deps = task.get("depends_on") or []
        if deps:
            line += f" — önce: {', '.join(deps)}"
        lines.append(line)
    if plan_approval:
        lines.append("(plan_approval açık → yürütme onayını bekleyecek)")
    return "\n".join(lines)
