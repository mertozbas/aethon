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
                channel: str = "") -> str:
        """Add a scheduled SOP job.

        Args:
            job_id: Unique job identifier.
            cron: Cron expression (e.g. "0 9 * * 1-5").
            sop_name: SOP to execute.
            channel: Channel to send results to.

        Returns:
            Job ID.
        """
        from apscheduler.triggers.cron import CronTrigger

        trigger = CronTrigger.from_crontab(cron)
        self.scheduler.add_job(
            self._run_sop,
            trigger=trigger,
            id=job_id,
            args=[sop_name, channel or self.default_channel],
            replace_existing=True,
        )
        self._jobs_meta[job_id] = {
            "cron": cron,
            "sop_name": sop_name,
            "channel": channel or self.default_channel,
        }
        logger.info(f"Gorev zamanlandi: {job_id} -> {sop_name} ({cron})")
        return job_id

    async def _run_sop(self, sop_name: str, channel: str) -> None:
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
                        recipient_id="default",
                        text=f"[Zamanlanmis: {sop_name}]\n\n{result}",
                    )
                    await gw.adapters[channel].send(msg)

            logger.info(f"Zamanlanmis gorev tamamlandi: {sop_name}")
        except Exception as e:
            logger.error(f"Zamanlanmis gorev hatasi ({sop_name}): {e}")

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Returns:
            True if removed, False if not found.
        """
        try:
            self.scheduler.remove_job(job_id)
            self._jobs_meta.pop(job_id, None)
            return True
        except Exception:
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
        logger.info("Zamanlayici baslatildi")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Zamanlayici durduruldu")


# --- Agent Tools ---


@tool
def schedule_task(cron_expression: str, sop_name: str, job_id: str = "",
                  channel: str = "") -> str:
    """Zamanlanmis gorev olustur veya guncelle. Belirtilen cron zamaninda SOP calistirir.

    Args:
        cron_expression: Cron ifadesi (orn: "0 9 * * 1-5" hafta ici sabah 9)
        sop_name: Calistirilacak SOP adi
        job_id: Gorev ID (bos ise otomatik olusturulur)
        channel: Sonucun gonderilecegi kanal (bos ise varsayilan)
    """
    if not _scheduler_instance:
        return "Hata: Zamanlayici baslatilmamis."
    if not job_id:
        job_id = f"task-{uuid.uuid4().hex[:8]}"
    try:
        _scheduler_instance.add_job(job_id, cron_expression, sop_name, channel)
        return f"Gorev zamanlandi: {job_id} -> {sop_name} ({cron_expression})"
    except Exception as e:
        return f"Hata: Gorev zamanlanamadi ({e})"


@tool
def list_scheduled_jobs() -> str:
    """Zamanlanmis tum gorevleri listele."""
    if not _scheduler_instance:
        return "Hata: Zamanlayici baslatilmamis."
    jobs = _scheduler_instance.list_jobs()
    if not jobs:
        return "Zamanlanmis gorev yok."
    lines = []
    for j in jobs:
        lines.append(
            f"- {j['job_id']}: {j['sop_name']} ({j['cron']}) -> {j['channel']} "
            f"[sonraki: {j['next_run']}]"
        )
    return "\n".join(lines)


@tool
def remove_scheduled_job(job_id: str) -> str:
    """Zamanlanmis gorevi kaldir.

    Args:
        job_id: Kaldirilacak gorev ID'si
    """
    if not _scheduler_instance:
        return "Hata: Zamanlayici baslatilmamis."
    if _scheduler_instance.remove_job(job_id):
        return f"Gorev kaldirildi: {job_id}"
    return f"Gorev bulunamadi: {job_id}"
