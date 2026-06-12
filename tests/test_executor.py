"""Tests for the bounded project executor (Phase 10 C3)."""

import re

import pytest

from aethon.agent.executor import ProjectExecutor
from aethon.agent.task_ledger import TaskLedger
from aethon.config import AethonConfig


def _config():
    return AethonConfig()


class _FakeMeter:
    def __init__(self, over=False):
        self._over = over

    def over_budget(self):
        return self._over


class _FakeRuntime:
    """Minimal runtime stand-in: a real ledger + config + a stub process()."""
    def __init__(self, ledger, config, completer):
        self._task_ledger = ledger
        self.config = config
        self.token_meter = _FakeMeter()
        self._completer = completer

    async def process(self, msg, session_id):
        await self._completer(msg, session_id, self._task_ledger)
        return "ok"


async def _complete_current(msg, session_id, ledger):
    """Simulate an agent that finishes the task named in the turn text."""
    m = re.search(r"\[(T\d+)\]", msg.text)
    if m:
        ledger.complete(m.group(1), evidence="done by fake agent")


async def _noop(msg, session_id, ledger):
    """An agent that never makes progress."""
    return None


def _project(tmp_path):
    led = TaskLedger(str(tmp_path))
    proj = led.create("Proje")
    return led, proj["id"]


@pytest.mark.asyncio
async def test_executor_runs_project_to_completion(tmp_path):
    led, pid = _project(tmp_path)
    led.create("A", parent_id=pid)                       # T2
    led.create("B", parent_id=pid, depends_on=["T2"])    # T3
    led.create("C", parent_id=pid, depends_on=["T3"])    # T4

    rt = _FakeRuntime(led, _config(), _complete_current)
    result = await ProjectExecutor(rt).run(pid)

    assert result["reason"] == "complete"
    assert result["iterations"] == 3                     # one turn per task, in order
    assert set(result["done"]) == {"T2", "T3", "T4"}
    assert result["remaining"] == []
    assert led.is_project_complete(pid)


@pytest.mark.asyncio
async def test_executor_respects_iteration_cap(tmp_path):
    led, pid = _project(tmp_path)
    for i in range(5):
        led.create(f"t{i}", parent_id=pid)
    config = _config()
    config.core_loop.executor_max_iterations = 2

    rt = _FakeRuntime(led, config, _noop)               # never completes anything
    result = await ProjectExecutor(rt).run(pid)

    assert result["reason"] == "cap"
    assert result["iterations"] == 2                     # stopped at the cap


@pytest.mark.asyncio
async def test_executor_stops_when_stuck(tmp_path):
    led, pid = _project(tmp_path)
    led.create("hard", parent_id=pid)                    # T2
    config = _config()
    config.core_loop.executor_max_task_attempts = 2

    rt = _FakeRuntime(led, config, _noop)
    result = await ProjectExecutor(rt).run(pid)

    assert result["reason"] == "stuck"
    assert result["stuck"] == "T2"
    assert result["iterations"] == 2                     # 2 attempts, then give up


@pytest.mark.asyncio
async def test_executor_stops_on_budget_between_tasks(tmp_path):
    led, pid = _project(tmp_path)
    led.create("a", parent_id=pid)

    rt = _FakeRuntime(led, _config(), _complete_current)
    rt.token_meter = _FakeMeter(over=True)               # already over the ceiling
    result = await ProjectExecutor(rt).run(pid)

    assert result["reason"] == "budget"
    assert result["iterations"] == 0                     # never even started a task


@pytest.mark.asyncio
async def test_executor_blocked_when_no_task_available(tmp_path):
    led, pid = _project(tmp_path)
    led.create("orphan", parent_id=pid, depends_on=["T999"])  # never satisfiable

    rt = _FakeRuntime(led, _config(), _complete_current)
    result = await ProjectExecutor(rt).run(pid)

    assert result["reason"] == "blocked"
    assert "T2" in result["remaining"]
    assert result["iterations"] == 0


@pytest.mark.asyncio
async def test_executor_resumes_after_restart(tmp_path):
    """Checkpoint + resume: the ledger IS the durable checkpoint. A run capped
    mid-project finishes only some tasks; a fresh ledger + executor (a restart)
    reads the persisted state and completes the rest."""
    led, pid = _project(tmp_path)
    led.create("A", parent_id=pid)                       # T2
    led.create("B", parent_id=pid, depends_on=["T2"])    # T3

    cfg1 = _config()
    cfg1.core_loop.executor_max_iterations = 1           # only one task this run
    r1 = await ProjectExecutor(_FakeRuntime(led, cfg1, _complete_current)).run(pid)
    assert r1["reason"] == "cap"
    assert r1["done"] == ["T2"]

    # "Restart": a brand-new ledger instance on the same file + a new executor.
    led2 = TaskLedger(str(tmp_path))
    r2 = await ProjectExecutor(_FakeRuntime(led2, _config(), _complete_current)).run(pid)
    assert r2["reason"] == "complete"
    assert "T3" in r2["done"]
    assert led2.is_project_complete(pid)


# --- ambient promotion (C3 integration) ---


@pytest.mark.asyncio
async def test_ambient_delegates_to_executor_when_enabled(tmp_path):
    from aethon.agent.ambient import AmbientModeManager

    led, pid = _project(tmp_path)
    led.create("A", parent_id=pid)
    config = _config()
    config.core_loop.executor_enabled = True
    rt = _FakeRuntime(led, config, _complete_current)

    mgr = AmbientModeManager(rt, config)
    result = await mgr._maybe_run_executor()
    assert result is not None
    assert result["reason"] == "complete"
    assert "T2" in result["done"]


@pytest.mark.asyncio
async def test_ambient_executor_noop_when_disabled(tmp_path):
    from aethon.agent.ambient import AmbientModeManager

    led, pid = _project(tmp_path)
    led.create("A", parent_id=pid)
    config = _config()  # executor_enabled is False by default
    rt = _FakeRuntime(led, config, _complete_current)

    mgr = AmbientModeManager(rt, config)
    assert await mgr._maybe_run_executor() is None
    # The project was not touched.
    assert led.get("T2")["status"] == "open"
