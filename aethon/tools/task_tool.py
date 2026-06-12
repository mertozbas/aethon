"""Task ledger tool (Phase 8 / R9).

Provides the manage_tasks tool bound to the workspace TaskLedger.
Uses the closure pattern (same as context_tool.py / memory_tool.py).
"""

import json

from strands import tool

from aethon.agent.task_ledger import (
    VALID_PRIORITIES,
    VALID_STATUSES,
    TaskLedger,
)


def _parse_depends_on(raw: str) -> list[str]:
    """Parse the agent-supplied depends_on into a list of ids. Accepts a JSON
    array (``["T1","T2"]``) or a comma/pipe-separated string (``T1, T2``)."""
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                # Keep only scalar ids — a nested list/object element would
                # otherwise stringify to its repr (e.g. "['T1']") and reach the
                # snapshot as a junk dependency (review fix).
                return [
                    str(d).strip()
                    for d in data
                    if isinstance(d, (str, int)) and str(d).strip()
                ]
        except (json.JSONDecodeError, ValueError):
            pass  # fall through to delimiter parsing
    return [part.strip() for part in raw.replace("|", ",").split(",") if part.strip()]


def create_task_tool(ledger: TaskLedger):
    """Create a manage_tasks tool bound to a TaskLedger instance."""

    @tool
    def manage_tasks(
        action: str,
        task_id: str = "",
        title: str = "",
        acceptance_criteria: str = "",
        status: str = "",
        evidence: str = "",
        plan_origin: str = "",
        parent_id: str = "",
        depends_on: str = "",
        priority: str = "",
        due: str = "",
    ) -> str:
        """Manage the persistent task ledger (workspace/TASKS.json).

        The ledger survives session resets and restarts — it is your durable
        working state. Create a task for any multi-step work (record what
        "done" means in acceptance_criteria), keep statuses current, and
        complete tasks WITH verification evidence (e.g. test output). If you
        deviate from a planned task, say so and update the ledger first.

        For a multi-task project, set parent_id to the project task's id and use
        depends_on to order the work — a task only becomes available once every
        task it depends on is done.

        Args:
            action: "create" | "update" | "complete" | "list"
            task_id: Task id for update/complete (e.g. "T3")
            title: Task title (create; optionally update)
            acceptance_criteria: Concrete definition of done for the task
            status: New status for update — open|in_progress|done|dropped
            evidence: Verification evidence (complete; optionally update)
            plan_origin: Where the task came from (plan/user request)
            parent_id: The project (parent task) this task belongs to
            depends_on: Task ids that must be done first — JSON list or "T1,T2"
            priority: critical | high | medium | low (default medium)
            due: Optional deadline note (e.g. an ISO timestamp)
        """
        if action == "create":
            if not title:
                return "Error: 'title' is required."
            deps = _parse_depends_on(depends_on)
            if priority and priority.lower() not in VALID_PRIORITIES:
                return (
                    f"Error: invalid priority {priority!r}. "
                    f"Valid: {', '.join(VALID_PRIORITIES)}"
                )
            if parent_id and ledger.get(parent_id) is None:
                return f"Error: parent_id references unknown task: {parent_id}"
            problems = ledger.dependency_problems("", deps)
            if problems:
                return "Error: " + "; ".join(problems)
            task = ledger.create(
                title, acceptance_criteria=acceptance_criteria,
                plan_origin=plan_origin,
                parent_id=parent_id, depends_on=deps,
                priority=priority or "medium", due=due,
            )
            return f"Task created: [{task['id']}] {task['title']}"

        if action == "update":
            if not task_id:
                return "Error: 'task_id' is required."
            if status and status not in VALID_STATUSES:
                return (
                    f"Error: invalid status {status!r}. "
                    f"Valid: {', '.join(VALID_STATUSES)}"
                )
            if priority and priority.lower() not in VALID_PRIORITIES:
                return (
                    f"Error: invalid priority {priority!r}. "
                    f"Valid: {', '.join(VALID_PRIORITIES)}"
                )
            if parent_id and ledger.get(parent_id) is None:
                return f"Error: parent_id references unknown task: {parent_id}"
            deps = _parse_depends_on(depends_on) if depends_on else None
            if deps is not None:
                problems = ledger.dependency_problems(task_id, deps)
                if problems:
                    return "Error: " + "; ".join(problems)
            task = ledger.update(
                task_id,
                title=title or None,
                acceptance_criteria=acceptance_criteria or None,
                status=status or None,
                evidence=evidence or None,
                plan_origin=plan_origin or None,
                parent_id=parent_id or None,
                depends_on=deps,
                priority=priority or None,
                due=due or None,
            )
            if task is None:
                return f"Task not found: {task_id}"
            return f"Task updated: [{task['id']}] ({task['status']}) {task['title']}"

        if action == "complete":
            if not task_id:
                return "Error: 'task_id' is required."
            if not evidence:
                return (
                    "Error: 'evidence' is required to complete a task — record "
                    "how the result was verified (e.g. test/lint output)."
                )
            task = ledger.complete(task_id, evidence=evidence)
            if task is None:
                return f"Task not found: {task_id}"
            return f"Task completed: [{task['id']}] {task['title']}"

        if action == "list":
            tasks = ledger.list(status=status or None)
            if not tasks:
                return "Task ledger is empty." if not status else (
                    f"No tasks with status {status!r}."
                )
            return json.dumps(tasks, ensure_ascii=False, indent=2)

        return f"Unknown action: {action}. Supported: create, update, complete, list"

    return manage_tasks
