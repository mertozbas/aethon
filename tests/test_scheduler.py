"""Tests for AethonScheduler and scheduler tools."""

import asyncio
import pytest
from unittest.mock import MagicMock

from aethon.tools.scheduler import (
    AethonScheduler, set_scheduler,
    schedule_task, list_scheduled_jobs, remove_scheduled_job,
)


@pytest.fixture
def mock_runtime():
    runtime = MagicMock()
    runtime.get_or_create_agent.return_value = MagicMock()
    return runtime


@pytest.fixture
def mock_sop_runner():
    runner = MagicMock()
    runner.run_sop.return_value = "SOP sonucu"
    return runner


@pytest.fixture
def scheduler(mock_sop_runner, mock_runtime, tmp_path):
    sched = AethonScheduler(
        mock_sop_runner, mock_runtime, "telegram",
        store_path=str(tmp_path / "SCHEDULE.json"),
    )
    return sched


@pytest.fixture(autouse=True)
def cleanup():
    yield
    set_scheduler(None)


def test_scheduler_creation(scheduler):
    """AethonScheduler can be created."""
    assert scheduler.sop_runner is not None
    assert scheduler.runtime is not None
    assert scheduler.default_channel == "telegram"


def test_scheduler_add_job(scheduler):
    """add_job adds job to scheduler."""
    job_id = scheduler.add_job("test-job", "0 9 * * *", "morning-brief")
    assert job_id == "test-job"
    assert "test-job" in scheduler._jobs_meta
    assert scheduler._jobs_meta["test-job"]["sop_name"] == "morning-brief"


def test_scheduler_recipient_used_for_delivery(scheduler, monkeypatch):
    """A job's recipient is sent as the OutboundMessage recipient_id (not hardcoded 'default')."""
    import aethon.tools.messaging as messaging_module

    sent = {}

    class FakeAdapter:
        async def send(self, msg):
            sent["channel"] = msg.channel
            sent["recipient_id"] = msg.recipient_id

    fake_gw = MagicMock()
    fake_gw.adapters = {"telegram": FakeAdapter()}
    monkeypatch.setattr(messaging_module, "get_gateway", lambda: fake_gw)

    scheduler.add_job("j", "0 9 * * *", "morning-brief", channel="telegram", recipient="123456789")
    assert scheduler._jobs_meta["j"]["recipient"] == "123456789"

    asyncio.run(scheduler._run_sop("morning-brief", "telegram", "123456789"))
    assert sent["channel"] == "telegram"
    assert sent["recipient_id"] == "123456789"  # the real chat id, not 'default'


def test_scheduler_list_jobs(scheduler):
    """list_jobs returns correct data."""
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    scheduler.add_job("j2", "0 18 * * 5", "sop2", "slack")
    jobs = scheduler.list_jobs()
    assert len(jobs) == 2
    names = [j["sop_name"] for j in jobs]
    assert "sop1" in names
    assert "sop2" in names


def test_scheduler_remove_job(scheduler):
    """remove_job removes existing job."""
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    assert scheduler.remove_job("j1") is True
    assert scheduler.list_jobs() == []


def test_scheduler_remove_nonexistent(scheduler):
    """remove_job returns False for missing job."""
    assert scheduler.remove_job("nonexistent") is False


def test_scheduler_default_channel(scheduler):
    """Job uses default channel when none specified."""
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    assert scheduler._jobs_meta["j1"]["channel"] == "telegram"


def test_scheduler_custom_channel(scheduler):
    """Job uses custom channel when specified."""
    scheduler.add_job("j1", "0 9 * * *", "sop1", "discord")
    assert scheduler._jobs_meta["j1"]["channel"] == "discord"


@pytest.mark.asyncio
async def test_concurrent_scheduled_sops_serialize(mock_runtime, tmp_path):
    """Two scheduled SOPs firing in the same window must not run concurrently:
    they share the one 'scheduler:cron' agent + its session file, so _run_lock
    serializes them (review fix). Without the lock both run_sop calls land in
    the executor threadpool at once and max in-flight would be 2."""
    import threading
    import time

    state = {"active": 0, "max": 0}
    guard = threading.Lock()

    class SlowRunner:
        def run_sop(self, sop_name, agent, text, invoke):
            with guard:
                state["active"] += 1
                state["max"] = max(state["max"], state["active"])
            time.sleep(0.05)
            with guard:
                state["active"] -= 1
            return "ok"

    sched = AethonScheduler(
        SlowRunner(), mock_runtime, "telegram",
        store_path=str(tmp_path / "SCHEDULE.json"),
    )
    # channel="" → _deliver short-circuits; we only care about run overlap.
    await asyncio.gather(
        sched._run_config_sop("a", "", ""),
        sched._run_config_sop("b", "", ""),
    )
    assert state["max"] == 1  # never two scheduled SOPs in flight at once


@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler):
    """Scheduler can start and stop in async context."""
    scheduler.start()
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    jobs = scheduler.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["next_run"] is not None
    scheduler.stop()


def test_schedule_task_tool_no_scheduler():
    """schedule_task returns error without scheduler."""
    result = schedule_task._tool_func(
        cron_expression="0 9 * * *", sop_name="test"
    )
    assert "Error" in result


def test_schedule_task_tool_with_scheduler(scheduler):
    """schedule_task creates job via scheduler."""
    set_scheduler(scheduler)
    result = schedule_task._tool_func(
        cron_expression="0 9 * * *", sop_name="morning", job_id="test-tool"
    )
    assert "scheduled" in result
    assert "test-tool" in result


def test_list_scheduled_jobs_tool_empty(scheduler):
    """list_scheduled_jobs returns message when empty."""
    set_scheduler(scheduler)
    result = list_scheduled_jobs._tool_func()
    assert "No scheduled tasks" in result


def test_list_scheduled_jobs_tool_with_jobs(scheduler):
    """list_scheduled_jobs lists all jobs."""
    set_scheduler(scheduler)
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    result = list_scheduled_jobs._tool_func()
    assert "j1" in result
    assert "sop1" in result


def test_remove_scheduled_job_tool(scheduler):
    """remove_scheduled_job removes job."""
    set_scheduler(scheduler)
    scheduler.add_job("j1", "0 9 * * *", "sop1")
    result = remove_scheduled_job._tool_func(job_id="j1")
    assert "removed" in result


def test_remove_scheduled_job_tool_missing(scheduler):
    """remove_scheduled_job reports missing job."""
    set_scheduler(scheduler)
    result = remove_scheduled_job._tool_func(job_id="nonexistent")
    assert "not found" in result


# --- H4: persistence, DateTrigger one-shot, free-text prompt -----------------


def test_runtime_job_persists_and_restores(mock_sop_runner, mock_runtime, tmp_path):
    """A runtime-scheduled job survives a simulated restart (SCHEDULE.json)."""
    store = str(tmp_path / "SCHEDULE.json")
    a = AethonScheduler(mock_sop_runner, mock_runtime, "telegram", store_path=store)
    a.schedule(job_id="j1", cron="0 9 * * *", prompt="günaydın de", channel="telegram",
               recipient="42")
    assert (tmp_path / "SCHEDULE.json").exists()

    # Fresh scheduler (simulated restart) reloads it.
    b = AethonScheduler(mock_sop_runner, mock_runtime, "telegram", store_path=store)
    assert b.load_persisted() == 1
    assert "j1" in b._jobs_meta
    assert b._jobs_meta["j1"]["prompt"] == "günaydın de"


def test_config_jobs_not_persisted(mock_sop_runner, mock_runtime, tmp_path):
    """add_job (config jobs) must NOT be written to SCHEDULE.json."""
    store = tmp_path / "SCHEDULE.json"
    a = AethonScheduler(mock_sop_runner, mock_runtime, "telegram", store_path=str(store))
    a.add_job("cfg", "0 9 * * *", "sop1")
    a.schedule(job_id="rt", cron="0 9 * * *", sop_name="sop2")  # runtime → persisted
    import json as _json

    data = _json.loads(store.read_text())
    ids = [j["job_id"] for j in data["jobs"]]
    assert ids == ["rt"]  # only the runtime job


def test_schedule_validates_one_trigger_one_payload(scheduler):
    import pytest as _pytest

    with _pytest.raises(ValueError):
        scheduler.schedule(job_id="x", sop_name="s")  # no trigger
    with _pytest.raises(ValueError):
        scheduler.schedule(job_id="x", cron="0 9 * * *", run_at="2026-01-01T00:00")  # two
    with _pytest.raises(ValueError):
        scheduler.schedule(job_id="x", cron="0 9 * * *", sop_name="s", prompt="p")  # two payloads


@pytest.mark.asyncio
async def test_one_shot_date_job_registers(scheduler):
    """A run_at one-shot uses a DateTrigger and registers a job."""
    scheduler.start()
    scheduler.schedule(job_id="once", run_at="2999-01-01T09:00", prompt="hatırlat")
    jobs = scheduler.list_jobs()
    assert any(j["job_id"] == "once" for j in jobs)
    scheduler.stop()


def test_missed_one_shot_recovered_on_load(mock_sop_runner, mock_runtime, tmp_path):
    """A one-shot whose time passed while down is recovered (rescheduled soon)."""
    import json as _json

    store = tmp_path / "SCHEDULE.json"
    store.write_text(_json.dumps({"version": 1, "jobs": [{
        "job_id": "missed", "cron": "", "run_at": "2000-01-01T00:00:00",
        "sop_name": "", "prompt": "geç kalan", "channel": "telegram",
        "recipient": "1", "persistent": True,
    }]}))
    sched = AethonScheduler(mock_sop_runner, mock_runtime, "telegram", store_path=str(store))
    assert sched.load_persisted() == 1
    # run_at was rewritten to the near future (recovered), not left in 2000.
    assert not sched._jobs_meta["missed"]["run_at"].startswith("2000")
