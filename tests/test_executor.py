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


def _project_with_origin(tmp_path, channel="telegram", recipient="123"):
    led = TaskLedger(str(tmp_path))
    proj = led.create("Web API")
    led.update(proj["id"], origin_channel=channel, origin_recipient=recipient)
    return led, proj["id"]


def _capture(ex):
    """Monkeypatch the executor's delivery to record (channel, recipient, text)."""
    sent = []

    async def _deliver(channel, recipient, text):
        sent.append((channel, recipient, text))

    ex._deliver = _deliver
    return sent


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
async def test_executor_drops_stuck_task_durably(tmp_path):
    """Review fix (runaway): a task the agent can't finish is dropped after its
    attempt limit — DURABLY (status='dropped'), so it leaves available_tasks and
    can't be retried on a later tick or after a restart with a reset counter."""
    led, pid = _project(tmp_path)
    led.create("hard", parent_id=pid)                    # T2
    config = _config()
    config.core_loop.executor_max_task_attempts = 2

    result = await ProjectExecutor(_FakeRuntime(led, config, _noop)).run(pid)
    assert result["reason"] == "partial"
    assert result["dropped"] == ["T2"]
    assert result["iterations"] == 2                     # 2 attempts, then dropped
    assert led.get("T2")["status"] == "dropped"          # durable
    assert led.get("T2")["executor_attempts"] == 2       # counter persisted


@pytest.mark.asyncio
async def test_executor_attempt_limit_survives_reinvocation(tmp_path):
    """The attempt limit is GLOBAL, not per-run: a stuck task is not re-attempted
    on a fresh executor (the in-memory-counter-reset runaway hole)."""
    led, pid = _project(tmp_path)
    led.create("hard", parent_id=pid)                    # T2
    config = _config()
    config.core_loop.executor_max_task_attempts = 2

    # First run drops T2 after 2 attempts.
    await ProjectExecutor(_FakeRuntime(led, config, _noop)).run(pid)
    assert led.get("T2")["status"] == "dropped"

    # A brand-new executor + fresh ledger (a restart) must NOT re-attempt it.
    led2 = TaskLedger(str(tmp_path))
    calls = {"n": 0}

    async def _count(msg, sid, ledger):
        calls["n"] += 1

    r2 = await ProjectExecutor(_FakeRuntime(led2, config, _count)).run(pid)
    assert calls["n"] == 0                               # dropped task never re-run
    assert r2["iterations"] == 0
    assert r2["reason"] == "partial"                     # remembers the drop


@pytest.mark.asyncio
async def test_executor_does_not_revert_concurrently_completed_task(tmp_path, monkeypatch):
    """Review fix (concurrency): if a task is completed between the
    available_tasks read and the in_progress write, the executor must not revert
    it to in_progress."""
    led, pid = _project(tmp_path)
    led.create("A", parent_id=pid)                       # T2, open

    rt = _FakeRuntime(led, _config(), _noop)
    real_get = led.get

    def racing_get(task_id):
        # Simulate a user turn completing T2 right at the executor's re-check.
        task = real_get(task_id)
        if task_id == "T2" and task and task.get("status") != "done":
            led.complete("T2", evidence="concurrent user")
        return real_get(task_id)

    monkeypatch.setattr(led, "get", racing_get)
    result = await ProjectExecutor(rt).run(pid)

    fresh = TaskLedger(str(tmp_path))
    assert fresh.get("T2")["status"] == "done"           # guard prevented a revert
    assert result["iterations"] == 0                     # never drove a turn on it


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


# --- C4: pulse + proof-of-work receipt ---


@pytest.mark.asyncio
async def test_executor_delivers_receipt_with_real_evidence(tmp_path):
    """The receipt is the product's signature: not a bare 'done' but the real
    per-task evidence the ledger captured, delivered to the origin channel."""
    led, pid = _project_with_origin(tmp_path)
    led.create("A", parent_id=pid)
    led.create("B", parent_id=pid)

    ex = ProjectExecutor(_FakeRuntime(led, _config(), _complete_current))
    sent = _capture(ex)
    await ex.run(pid)

    receipts = [s for s in sent if "Bitti" in s[2]]
    assert receipts                                   # a receipt was delivered
    channel, recipient, text = receipts[-1]
    assert channel == "telegram" and recipient == "123"   # back to the origin
    assert "done by fake agent" in text               # REAL evidence, not "done"
    assert "✓ [T2]" in text and "✓ [T3]" in text


@pytest.mark.asyncio
async def test_executor_pulses_every_n_completions(tmp_path):
    led, pid = _project_with_origin(tmp_path)
    led.create("A", parent_id=pid)
    led.create("B", parent_id=pid)
    config = _config()
    config.core_loop.pulse_every_n_tasks = 1          # pulse on every completion

    ex = ProjectExecutor(_FakeRuntime(led, config, _complete_current))
    sent = _capture(ex)
    await ex.run(pid)

    pulses = [s for s in sent if "görev bitti" in s[2]]
    assert len(pulses) == 2                            # one per completed task


@pytest.mark.asyncio
async def test_executor_receipt_is_silenceable(tmp_path):
    led, pid = _project_with_origin(tmp_path)
    led.create("A", parent_id=pid)
    config = _config()
    config.core_loop.receipt_enabled = False
    config.core_loop.pulse_enabled = False

    ex = ProjectExecutor(_FakeRuntime(led, config, _complete_current))
    sent = _capture(ex)
    await ex.run(pid)

    assert sent == []                                 # nothing delivered


@pytest.mark.asyncio
async def test_executor_no_origin_skips_delivery(tmp_path):
    """A project with no origin (e.g. agent-initiated) delivers nothing and does
    not crash."""
    led, pid = _project(tmp_path)                     # no origin stamped
    led.create("A", parent_id=pid)

    ex = ProjectExecutor(_FakeRuntime(led, _config(), _complete_current))
    sent = _capture(ex)
    result = await ex.run(pid)

    assert sent == []
    assert result["reason"] == "complete"


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
