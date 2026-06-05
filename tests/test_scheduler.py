"""Tests for AethonScheduler and scheduler tools."""

import asyncio
import pytest
from unittest.mock import MagicMock

from aethon.tools.scheduler import (
    AethonScheduler, set_scheduler,
    schedule_task, list_scheduled_jobs, remove_scheduled_job,
)
import aethon.tools.scheduler as scheduler_module


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
def scheduler(mock_sop_runner, mock_runtime):
    sched = AethonScheduler(mock_sop_runner, mock_runtime, "telegram")
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
