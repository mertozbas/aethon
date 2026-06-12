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
import re
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aethon.tasks")

VALID_STATUSES = ("open", "in_progress", "done", "dropped")
# Priority ordering for the execution loop (Phase 10 C2/C3). Lower index = more
# urgent; the dependency resolver picks the most urgent *available* task.
VALID_PRIORITIES = ("critical", "high", "medium", "low")
_PRIORITY_RANK = {p: i for i, p in enumerate(VALID_PRIORITIES)}

# Optional Phase 10 C2 fields. Kept separate from the original flat schema so the
# additive (migration-safe) expansion stays auditable. Defaults are filled in on
# read by _normalize(), so a pre-Phase-10 TASKS.json loads without KeyErrors.
_C2_DEFAULTS = {
    "parent_id": "",      # the project (parent task) this task belongs to
    "depends_on": [],     # ids that must be 'done' before this task is available
    "priority": "medium",
    "due": "",            # optional ISO timestamp/free-text deadline note
}


class TaskLedger:
    """Manage TASKS.json with create/update/complete/list operations."""

    def __init__(self, workspace_dir: str):
        self.tasks_file = Path(workspace_dir).expanduser() / "TASKS.json"
        # Strands runs tools on a ConcurrentToolExecutor and the same ledger
        # instance is shared by every session — an unlocked load-mutate-save
        # cycle loses updates and duplicates ids under parallel tool calls.
        self._lock = threading.Lock()

    # ---- storage ----

    def _load(self) -> list[dict]:
        if not self.tasks_file.exists():
            return []
        try:
            data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                # Drop non-dict entries (a hand edit can leave a stray string or
                # null in an otherwise-valid list) — they would crash every
                # .get() downstream. Fail loud about the loss (review fix).
                valid = [t for t in data if isinstance(t, dict)]
                dropped = len(data) - len(valid)
                if dropped:
                    logger.warning(
                        "Task ledger had %d non-dict entr%s; ignoring them.",
                        dropped, "y" if dropped == 1 else "ies",
                    )
                # Backfill C2 fields on read so old ledgers load seamlessly.
                return [self._normalize(t) for t in valid]
            raise ValueError(f"expected a JSON list, got {type(data).__name__}")
        except Exception as e:
            # Quarantine instead of returning [] — the next create() would
            # otherwise silently overwrite the whole ledger with a fresh
            # file and restart ids at T1 (silent data loss for the one
            # component whose job is durability).
            quarantine = self.tasks_file.with_name(
                self.tasks_file.name + ".corrupt"
            )
            try:
                self.tasks_file.replace(quarantine)
                logger.error(
                    f"Task ledger unreadable ({e}); quarantined to "
                    f"{quarantine.name} and starting a fresh ledger."
                )
            except OSError as move_err:
                logger.error(
                    f"Task ledger unreadable ({e}) and quarantine failed "
                    f"({move_err})."
                )
            return []

    def _save(self, tasks: list[dict]) -> None:
        tmp = self.tasks_file.with_name(
            f".{self.tasks_file.name}.{threading.get_ident()}.tmp"
        )
        tmp.write_text(
            json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.tasks_file)  # atomic — a crashed write can't corrupt

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _flatten(value: str) -> str:
        """Collapse whitespace/newlines — ledger text reaches the system
        prompt, and embedded newlines could fabricate prompt layers."""
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _clean_priority(cls, priority: str) -> str:
        """Coerce to a valid priority; unknown values fall back to 'medium'
        (advisory — a bad priority must not block task creation)."""
        p = cls._flatten(str(priority or "")).lower()
        return p if p in VALID_PRIORITIES else "medium"

    @classmethod
    def _clean_depends_on(cls, depends_on) -> list[str]:
        """Normalize depends_on to a flat list of clean id strings. Accepts a
        list or a single value; non-strings are coerced and flattened so a
        stray title or newline can't smuggle a prompt layer through the id."""
        if depends_on is None:
            return []
        if isinstance(depends_on, str):
            depends_on = [depends_on]
        cleaned = []
        for dep in depends_on:
            dep = cls._flatten(str(dep))
            if dep:
                cleaned.append(dep)
        return cleaned

    @classmethod
    def _normalize(cls, task: dict) -> dict:
        """Fill in any missing/null Phase 10 C2 fields and coerce their types so
        a pre-Phase-10 TASKS.json or a hand edit (a missing key, an explicit
        ``null``, a non-list depends_on, a bogus priority) never crashes the
        sort/render path downstream (review fix). Operates on the ephemeral dict
        _load() just built, so the in-place fill is never shared across reads."""
        for key, default in _C2_DEFAULTS.items():
            if task.get(key) is None:  # missing OR explicit null
                task[key] = list(default) if isinstance(default, list) else default
        if not isinstance(task.get("depends_on"), list):
            task["depends_on"] = cls._clean_depends_on(task.get("depends_on"))
        if task.get("priority") not in VALID_PRIORITIES:
            task["priority"] = cls._clean_priority(task.get("priority"))
        return task

    # ---- operations ----

    def create(
        self,
        title: str,
        acceptance_criteria: str = "",
        plan_origin: str = "",
        *,
        parent_id: str = "",
        depends_on: list[str] | None = None,
        priority: str = "medium",
        due: str = "",
    ) -> dict:
        priority = self._clean_priority(priority)
        with self._lock:
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
                "title": self._flatten(title),
                "acceptance_criteria": self._flatten(acceptance_criteria),
                "status": "open",
                "evidence": "",
                "plan_origin": self._flatten(plan_origin),
                # Phase 10 C2 fields (additive, migration-safe).
                "parent_id": self._flatten(str(parent_id or "")),
                "depends_on": self._clean_depends_on(depends_on),
                "priority": priority,
                "due": self._flatten(str(due or "")),
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

    # Fields the original flat schema allowed update() to set.
    _UPDATABLE = ("title", "acceptance_criteria", "status", "evidence", "plan_origin")
    # Phase 10 C2 additions (separate tuple so the expansion stays auditable).
    # ``executor_attempts`` (C3) is a durable per-task try counter the executor
    # bumps so its attempt limit survives re-invocations and restarts.
    _UPDATABLE_C2 = ("parent_id", "priority", "due", "executor_attempts")

    def update(self, task_id: str, **fields) -> dict | None:
        """Update title/acceptance_criteria/status/evidence/plan_origin and the
        Phase 10 C2 fields parent_id/depends_on/priority/due."""
        status = fields.get("status")
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}; expected one of {VALID_STATUSES}"
            )
        with self._lock:
            tasks = self._load()
            for task in tasks:
                if task.get("id") == task_id:
                    for key in (*self._UPDATABLE, *self._UPDATABLE_C2):
                        value = fields.get(key)
                        if value is not None:
                            if key == "priority":
                                value = self._clean_priority(value)
                            task[key] = (
                                self._flatten(value)
                                if isinstance(value, str)
                                else value
                            )
                    # depends_on is a list — normalize separately.
                    if fields.get("depends_on") is not None:
                        task["depends_on"] = self._clean_depends_on(
                            fields["depends_on"]
                        )
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

    def children(self, parent_id: str) -> list[dict]:
        """Tasks belonging to a project (parent task)."""
        return [t for t in self._load() if t.get("parent_id") == parent_id]

    def active_project(self) -> str | None:
        """The id of the most recent project (parent task) that still has
        open/in_progress children — what the C3 executor should work next.
        ``None`` when no project has unfinished work. Most-recent = highest
        numeric id among such parents (ids are assigned in creation order).
        """
        open_parents = {
            t.get("parent_id")
            for t in self._load()
            if t.get("status") in ("open", "in_progress") and t.get("parent_id")
        }
        if not open_parents:
            return None

        def _num(pid: str) -> int:
            tail = str(pid)[1:]
            return int(tail) if tail.isdigit() else -1

        return max(open_parents, key=_num)

    def is_project_complete(self, parent_id: str) -> bool:
        """True when a project has children and none are still open/in_progress
        (every child is done or dropped). A project with no children is NOT
        complete — there is nothing finished to deliver."""
        kids = self.children(parent_id)
        if not kids:
            return False
        return not any(k.get("status") in ("open", "in_progress") for k in kids)

    @staticmethod
    def _reaches(start: str, target: str, adj: dict) -> bool:
        """Whether ``target`` is reachable from ``start``'s out-edges in the
        depends_on graph ``adj`` (used for cycle detection)."""
        seen: set = set()
        stack = list(adj.get(start, []))
        while stack:
            node = stack.pop()
            if node == target:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adj.get(node, []))
        return False

    def dependency_problems(self, task_id: str, depends_on: list[str]) -> list[str]:
        """Human-readable problems with a proposed depends_on edge — unknown
        references and dependency cycles — so the caller can reject a bad graph
        at write time instead of deadlocking the executor later (gap analysis).
        Empty list means the edge is sound.
        """
        depends_on = self._clean_depends_on(depends_on)
        # Reads an atomic _load() snapshot (lock-free, like every other query
        # here); validation is advisory — the executor's available_tasks() is the
        # real, fail-safe gate. A caller validate-then-write is not transactional.
        tasks = self._load()
        ids = {t.get("id") for t in tasks}
        problems = []
        unknown = [d for d in depends_on if d not in ids]
        if unknown:
            # Bound the message — a depends_on with thousands of bad ids must not
            # echo back as a 60KB error (review fix).
            shown = ", ".join(unknown[:10])
            extra = f" … and {len(unknown) - 10} more" if len(unknown) > 10 else ""
            problems.append(
                f"depends_on references unknown task(s): {shown}{extra}"
            )
        if task_id and task_id in depends_on:
            problems.append(f"a task cannot depend on itself ({task_id})")
        # A cycle can only be introduced against an existing task (a brand-new
        # task isn't referenced by anything yet).
        elif task_id and task_id in ids:
            adj = {t.get("id"): list(t.get("depends_on") or []) for t in tasks}
            adj[task_id] = list(depends_on)
            if self._reaches(task_id, task_id, adj):
                problems.append("depends_on would create a dependency cycle")
        return problems

    def available_tasks(self, parent_id: str | None = None) -> list[dict]:
        """Open tasks whose dependencies are all satisfied (status 'done'),
        ordered most-urgent-first (Phase 10 C2; the C3 executor picks the head).

        A dependency on an id that is missing or not yet done keeps the task
        blocked — so a broken/typo'd ``depends_on`` fails safe (the task simply
        never becomes available) rather than running out of order. Computed from
        a single ``_load()`` snapshot so the read is internally consistent.
        """
        tasks = self._load()
        # A dependency is satisfied once it is 'done' OR 'dropped' (an explicitly
        # cancelled task is out of the workflow — leaving it to block dependents
        # forever would deadlock the project). Read fix.
        done = {t.get("id") for t in tasks if t.get("status") in ("done", "dropped")}
        available = []
        for t in tasks:
            if t.get("status") not in ("open", "in_progress"):
                continue
            if parent_id is not None and t.get("parent_id") != parent_id:
                continue
            deps = t.get("depends_on") or []
            if all(dep in done for dep in deps):
                available.append(t)
        # Most urgent first; ties broken by ledger order (creation sequence).
        available.sort(
            key=lambda t: _PRIORITY_RANK.get(t.get("priority"), _PRIORITY_RANK["medium"])
        )
        return available

    # ---- prompt layer ----

    def snapshot(self, max_tasks: int = 10) -> str:
        """Compact markdown snapshot for the system-prompt layer."""
        pending = self.open_tasks()
        if not pending:
            return ""
        lines = []
        for task in pending[:max_tasks]:
            # Flatten defensively on render too — pre-sanitization files (or
            # hand edits) must not be able to fabricate prompt layers.
            title = self._flatten(str(task.get("title", "")))
            # Surface priority + dependencies so a planned project tree is a
            # visible plan in the prompt, not just a flat to-do list (C2).
            prio = self._flatten(str(task.get("priority", "medium")))
            line = f"- [{task['id']}] ({task['status']}, {prio}) {title}"
            if task.get("acceptance_criteria"):
                criteria = self._flatten(str(task["acceptance_criteria"]))
                line += f" — done when: {criteria}"
            deps = task.get("depends_on") or []
            if deps:
                clean = ", ".join(self._flatten(str(d)) for d in deps)
                line += f" — after: {clean}"
            lines.append(line)
        if len(pending) > max_tasks:
            lines.append(f"- … and {len(pending) - max_tasks} more")
        return "\n".join(lines)
