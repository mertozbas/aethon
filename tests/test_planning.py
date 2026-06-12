"""Tests for the plan → ledger pipeline (Phase 10 C2)."""

import pytest

from aethon.agent.planning import PlanSchema, PlanTask, persist_plan
from aethon.agent.task_ledger import TaskLedger
from aethon.tools import delegate


@pytest.fixture
def ledger(tmp_path):
    return TaskLedger(str(tmp_path))


@pytest.fixture(autouse=True)
def _reset_delegate():
    yield
    delegate.set_specialist_factory(None)
    delegate.set_plan_ledger(None)


def test_persist_plan_builds_dependency_ordered_tree(ledger):
    """A plan produces a parent project + child tasks with local-ref deps mapped
    to real ids, and available_tasks walks them in dependency+priority order."""
    plan = PlanSchema(
        project_title="Web app",
        tasks=[
            PlanTask(title="Setup", priority="high"),                       # pos 1
            PlanTask(title="Build", priority="critical", depends_on=["1"]),  # pos 2
            PlanTask(title="Docs", priority="low"),                          # pos 3
        ],
    )
    result = persist_plan(ledger, plan)
    assert result["project_id"] == "T1"
    assert result["task_ids"] == ["T2", "T3", "T4"]

    # Children belong to the project; the local dep "1" mapped to the real id T2.
    assert [t["id"] for t in ledger.children("T1")] == ["T2", "T3", "T4"]
    assert ledger.get("T3")["depends_on"] == ["T2"]

    # Dependency-ordered: T3 (critical) is blocked on T2; T2 (high) leads T4 (low).
    assert [t["id"] for t in ledger.available_tasks("T1")] == ["T2", "T4"]
    ledger.complete("T2", evidence="ok")
    assert [t["id"] for t in ledger.available_tasks("T1")] == ["T3", "T4"]


def test_persist_plan_empty_returns_none(ledger):
    assert persist_plan(ledger, PlanSchema(project_title="boş", tasks=[])) is None
    assert ledger.list() == []


def test_persist_plan_drops_bad_edge_but_keeps_plan(ledger):
    """A dependency on a non-existent position is dropped (logged), but the rest
    of the plan still lands — one bad edge can't sink the whole plan."""
    plan = PlanSchema(
        project_title="X",
        tasks=[
            PlanTask(title="A"),
            PlanTask(title="B", depends_on=["9"]),  # position 9 doesn't exist
        ],
    )
    result = persist_plan(ledger, plan)
    assert result["task_ids"] == ["T2", "T3"]
    assert ledger.get("T3")["depends_on"] == []  # bad edge dropped
    assert ledger.get("T3")["title"] == "B"      # task itself preserved


def test_persist_plan_survives_update_failure(ledger, monkeypatch):
    """Review fix: if setting one child's dependencies blows up, the plan still
    lands whole (the failure is isolated to that edge, not propagated to orphan
    the half-plan and trigger a free-text fallback)."""
    plan = PlanSchema(
        project_title="X",
        tasks=[
            PlanTask(title="A"),
            PlanTask(title="B", depends_on=["1"]),
            PlanTask(title="C", depends_on=["1"]),
        ],
    )
    real_update = ledger.update
    calls = {"n": 0}

    def flaky_update(task_id, **fields):
        if "depends_on" in fields:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient ledger glitch")
        return real_update(task_id, **fields)

    monkeypatch.setattr(ledger, "update", flaky_update)
    result = persist_plan(ledger, plan)

    assert result is not None                       # did NOT raise
    assert result["task_ids"] == ["T2", "T3", "T4"]  # all children persisted
    # T3's edge was the one that failed (dropped); T4's still set.
    assert ledger.get("T4")["depends_on"] == ["T2"]


def test_persist_plan_approval_note_in_summary(ledger):
    plan = PlanSchema(project_title="X", tasks=[PlanTask(title="A")])
    out = persist_plan(ledger, plan, plan_approval=True)["summary"]
    assert "plan_approval" in out and "onay" in out


# --- ask_planner wiring + fallback ---


class _FakePlanner:
    def __init__(self, plan, text):
        self._plan = plan
        self._text = text

    def structured_output(self, model, prompt):
        return self._plan

    def __call__(self, prompt):
        return self._text


class _FakeFactory:
    def __init__(self, planner):
        self._planner = planner

    def get(self, name):
        return self._planner


def test_ask_planner_persists_structured_plan(ledger):
    plan = PlanSchema(project_title="API", tasks=[PlanTask(title="Endpoint")])
    delegate.set_specialist_factory(_FakeFactory(_FakePlanner(plan, "free text")))
    delegate.set_plan_ledger(ledger)

    out = delegate.ask_planner._tool_func(planning_task="bir API yap")
    assert "[T1]" in out and "Endpoint" not in out.split("\n")[0]  # project header
    assert ledger.get("T2")["title"] == "Endpoint"  # persisted as a child


def test_ask_planner_falls_back_to_free_text(ledger):
    """No structured tasks → the free-text plan is returned and nothing is
    written to the ledger (the provider couldn't force structured output)."""
    empty = PlanSchema(project_title="", tasks=[])
    delegate.set_specialist_factory(_FakeFactory(_FakePlanner(empty, "1. do this")))
    delegate.set_plan_ledger(ledger)

    out = delegate.ask_planner._tool_func(planning_task="planla")
    assert out == "1. do this"
    assert ledger.list() == []
