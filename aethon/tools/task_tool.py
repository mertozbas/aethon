"""Task ledger tool (Phase 8 / R9).

Provides the manage_tasks tool bound to the workspace TaskLedger.
Uses the closure pattern (same as context_tool.py / memory_tool.py).
"""

import json

from strands import tool

from aethon.agent.task_ledger import VALID_STATUSES, TaskLedger


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
    ) -> str:
        """Manage the persistent task ledger (workspace/TASKS.json).

        The ledger survives session resets and restarts — it is your durable
        working state. Create a task for any multi-step work (record what
        "done" means in acceptance_criteria), keep statuses current, and
        complete tasks WITH verification evidence (e.g. test output). If you
        deviate from a planned task, say so and update the ledger first.

        Args:
            action: "create" | "update" | "complete" | "list"
            task_id: Task id for update/complete (e.g. "T3")
            title: Task title (create; optionally update)
            acceptance_criteria: Concrete definition of done for the task
            status: New status for update — open|in_progress|done|dropped
            evidence: Verification evidence (complete; optionally update)
            plan_origin: Where the task came from (plan/user request)
        """
        if action == "create":
            if not title:
                return "Error: 'title' is required."
            task = ledger.create(
                title, acceptance_criteria=acceptance_criteria,
                plan_origin=plan_origin,
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
            task = ledger.update(
                task_id,
                title=title or None,
                acceptance_criteria=acceptance_criteria or None,
                status=status or None,
                evidence=evidence or None,
                plan_origin=plan_origin or None,
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
