"""Cron-based task scheduler.

APScheduler integration for automatic SOP triggering with result delivery to channels.
"""

import logging
import uuid
from typing import Any

from strands import tool


logger = logging.getLogger("aethon.scheduler")

_scheduler_instance = None


def set_scheduler(scheduler):
    """Set the global scheduler reference."""
    global _scheduler_instance
    _scheduler_instance = scheduler


class AethonScheduler:
    """Cron-based SOP task scheduler."""

    def __init__(self, sop_runner, runtime, default_channel: str = "telegram"):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self.scheduler = AsyncIOScheduler()
        self.sop_runner = sop_runner
        self.runtime = runtime
        self.default_channel = default_channel
        self._jobs_meta: dict[str, dict] = {}

    def add_job(self, job_id: str, cron: str, sop_name: str,
                channel: str = "", recipient: str = "") -> str:
        """Add a scheduled SOP job.

        Args:
            job_id: Unique job identifier.
            cron: Cron expression (e.g. "0 9 * * 1-5").
            sop_name: SOP to execute.
            channel: Channel to send results to.
            recipient: Destination id on that channel (e.g. a Telegram/Discord
                chat/channel id). Not needed for ``cli``/``webchat``.

        Returns:
            Job ID.
        """
        from apscheduler.triggers.cron import CronTrigger

        ch = channel or self.default_channel
        if ch and ch not in ("cli", "webchat") and not recipient:
            logger.warning(
                f"Scheduled job '{job_id}' targets channel '{ch}' without a recipient; "
                f"delivery will likely fail. Set a recipient (e.g. a chat/channel id)."
            )

        trigger = CronTrigger.from_crontab(cron)
        self.scheduler.add_job(
            self._run_sop,
            trigger=trigger,
            id=job_id,
            args=[sop_name, ch, recipient],
            replace_existing=True,
        )
        self._jobs_meta[job_id] = {
            "cron": cron,
            "sop_name": sop_name,
            "channel": ch,
            "recipient": recipient,
        }
        logger.info(f"Task scheduled: {job_id} -> {sop_name} ({cron})")
        return job_id

    async def _run_sop(self, sop_name: str, channel: str, recipient: str = "") -> None:
        """Execute scheduled SOP and send result to channel."""
        try:
            agent = self.runtime.get_or_create_agent("scheduler:cron")
            result = self.sop_runner.run_sop(sop_name, agent)

            if channel:
                from aethon.tools.messaging import get_gateway
                from aethon.channels.base import OutboundMessage

                gw = get_gateway()
                if gw and channel in gw.adapters:
                    msg = OutboundMessage(
                        channel=channel,
                        recipient_id=recipient or "default",
                        text=f"[Scheduled: {sop_name}]\n\n{result}",
                    )
                    await gw.adapters[channel].send(msg)

            logger.info(f"Scheduled task completed: {sop_name}")
        except Exception as e:
            logger.error(f"Scheduled task error ({sop_name}): {e}")

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Returns:
            True if removed, False if not found.
        """
        try:
            self.scheduler.remove_job(job_id)
            self._jobs_meta.pop(job_id, None)
            return True
        except Exception as e:
            logger.warning(f"Job removal failed ({job_id}): {e}")
            return False

    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs."""
        result = []
        for job in self.scheduler.get_jobs():
            meta = self._jobs_meta.get(job.id, {})
            result.append({
                "job_id": job.id,
                "sop_name": meta.get("sop_name", ""),
                "cron": meta.get("cron", ""),
                "channel": meta.get("channel", ""),
                "next_run": str(nrt) if (nrt := getattr(job, "next_run_time", None)) else None,
            })
        return result

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# --- Agent Tools ---


@tool
def schedule_task(cron_expression: str, sop_name: str, job_id: str = "",
                  channel: str = "", recipient: str = "") -> str:
    """Create or update a scheduled task. Runs the SOP at the specified cron time.

    Args:
        cron_expression: Cron expression (e.g. "0 9 * * 1-5" for weekdays at 9 AM)
        sop_name: Name of the SOP to run
        job_id: Task ID (auto-generated if empty)
        channel: Channel to send the result to (default if empty)
        recipient: Destination id on that channel (e.g. a chat/channel id);
            not needed for cli/webchat
    """
    if not _scheduler_instance:
        return "Error: Scheduler not started."
    if not job_id:
        job_id = f"task-{uuid.uuid4().hex[:8]}"
    try:
        _scheduler_instance.add_job(job_id, cron_expression, sop_name, channel, recipient)
        return f"Task scheduled: {job_id} -> {sop_name} ({cron_expression})"
    except Exception as e:
        return f"Error: Could not schedule task ({e})"


@tool
def list_scheduled_jobs() -> str:
    """List all scheduled tasks."""
    if not _scheduler_instance:
        return "Error: Scheduler not started."
    jobs = _scheduler_instance.list_jobs()
    if not jobs:
        return "No scheduled tasks."
    lines = []
    for j in jobs:
        lines.append(
            f"- {j['job_id']}: {j['sop_name']} ({j['cron']}) -> {j['channel']} "
            f"[next: {j['next_run']}]"
        )
    return "\n".join(lines)


@tool
def remove_scheduled_job(job_id: str) -> str:
    """Remove a scheduled task.

    Args:
        job_id: ID of the task to remove
    """
    if not _scheduler_instance:
        return "Error: Scheduler not started."
    if _scheduler_instance.remove_job(job_id):
        return f"Task removed: {job_id}"
    return f"Task not found: {job_id}"
