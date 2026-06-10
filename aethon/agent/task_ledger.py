"""Persistent task ledger (Phase 8 / R9).

Durable, machine-readable working state — the spine that connects
continuity (FM2), plan-drift visibility (FM3) and the verification gate
(FM1). Tasks live in ``workspace/TASKS.json``; a compact snapshot is
injected into the system prompt as the ``## Open Tasks`` layer, so state
survives agent-cache eviction, session resets and process restarts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aethon.tasks")

VALID_STATUSES = ("open", "in_progress", "done", "dropped")


class TaskLedger:
    """Manage TASKS.json with create/update/complete/list operations."""

    def __init__(self, workspace_dir: str):
        self.tasks_file = Path(workspace_dir).expanduser() / "TASKS.json"

    # ---- storage ----

    def _load(self) -> list[dict]:
        if not self.tasks_file.exists():
            return []
        try:
            data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Task ledger unreadable ({self.tasks_file}): {e}")
            return []

    def _save(self, tasks: list[dict]) -> None:
        tmp = self.tasks_file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.tasks_file)  # atomic — a crashed write can't corrupt

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    # ---- operations ----

    def create(
        self, title: str, acceptance_criteria: str = "", plan_origin: str = ""
    ) -> dict:
        tasks = self._load()
        next_num = 1 + max(
            [
                int(str(t.get("id", ""))[1:])
                for t in tasks
                if str(t.get("id", ""))[1:].isdigit()
            ]
            or [0]
        )
        task = {
            "id": f"T{next_num}",
            "title": title.strip(),
            "acceptance_criteria": acceptance_criteria.strip(),
            "status": "open",
            "evidence": "",
            "plan_origin": plan_origin.strip(),
            "created": self._now(),
            "updated": self._now(),
        }
        tasks.append(task)
        self._save(tasks)
        return task

    def get(self, task_id: str) -> dict | None:
        for task in self._load():
            if task.get("id") == task_id:
                return task
        return None

    def update(self, task_id: str, **fields) -> dict | None:
        """Update title/acceptance_criteria/status/evidence/plan_origin."""
        status = fields.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}; expected one of {VALID_STATUSES}"
            )
        tasks = self._load()
        for task in tasks:
            if task.get("id") == task_id:
                for key in (
                    "title", "acceptance_criteria", "status", "evidence",
                    "plan_origin",
                ):
                    value = fields.get(key)
                    if value is not None:
                        task[key] = value.strip() if isinstance(value, str) else value
                task["updated"] = self._now()
                self._save(tasks)
                return task
        return None

    def complete(self, task_id: str, evidence: str = "") -> dict | None:
        return self.update(task_id, status="done", evidence=evidence)

    def list(self, status: str | None = None) -> list[dict]:
        tasks = self._load()
        if status is None:
            return tasks
        return [t for t in tasks if t.get("status") == status]

    def open_tasks(self) -> list[dict]:
        """Tasks that still need work (open or in_progress)."""
        return [
            t for t in self._load() if t.get("status") in ("open", "in_progress")
        ]

    # ---- prompt layer ----

    def snapshot(self, max_tasks: int = 10) -> str:
        """Compact markdown snapshot for the system-prompt layer."""
        pending = self.open_tasks()
        if not pending:
            return ""
        lines = []
        for task in pending[:max_tasks]:
            line = f"- [{task['id']}] ({task['status']}) {task['title']}"
            if task.get("acceptance_criteria"):
                line += f" — done when: {task['acceptance_criteria']}"
            lines.append(line)
        if len(pending) > max_tasks:
            lines.append(f"- … and {len(pending) - max_tasks} more")
        return "\n".join(lines)
