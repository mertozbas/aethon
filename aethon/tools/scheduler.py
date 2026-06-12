"""Task scheduler.

APScheduler integration for automatic SOP / free-text triggering with result
delivery to channels. Runtime-added jobs are persisted to SCHEDULE.json and
reloaded at boot (Phase 9B / H4), support one-shot DateTriggers ("remind me
tomorrow at 15:30"), and can carry a free-text prompt run via runtime.process —
not only named SOPs.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from strands import tool


logger = logging.getLogger("aethon.scheduler")

_scheduler_instance = None

# How late a missed run may still fire (APScheduler misfire grace).
_MISFIRE_GRACE = 3600


def set_scheduler(scheduler):
    """Set the global scheduler reference."""
    global _scheduler_instance
    _scheduler_instance = scheduler


class AethonScheduler:
    """Cron + one-shot task scheduler with persistence."""

    def __init__(self, sop_runner, runtime, default_channel: str = "telegram",
                 store_path: str | None = None):
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        self.scheduler = AsyncIOScheduler()
        self.sop_runner = sop_runner
        self.runtime = runtime
        self.default_channel = default_channel
        self._jobs_meta: dict[str, dict] = {}
        # Serialize ALL scheduled execution (review fix): every scheduled turn
        # uses the one "scheduler:cron" agent, so two jobs firing in the same
        # window would otherwise race that agent + its session file.
        self._run_lock = asyncio.Lock()
        if store_path:
            self._store_path = Path(store_path).expanduser()
        else:
            workspace = Path(getattr(runtime, "config", None).paths.workspace).expanduser()
            self._store_path = workspace / "SCHEDULE.json"

    # --- registration ------------------------------------------------------

    def _trigger(self, *, cron: str = "", run_at: str = ""):
        if cron:
            from apscheduler.triggers.cron import CronTrigger

            return CronTrigger.from_crontab(cron)
        from apscheduler.triggers.date import DateTrigger

        return DateTrigger(run_date=datetime.fromisoformat(run_at))

    def add_job(self, job_id: str, cron: str, sop_name: str,
                channel: str = "", recipient: str = "") -> str:
        """Add a recurring SOP job (config-defined jobs use this; not persisted).

        Runtime jobs go through :meth:`schedule` so they survive restarts.
        """
        ch = channel or self.default_channel
        if ch and ch not in ("cli", "webchat") and not recipient:
            logger.warning(
                f"Scheduled job '{job_id}' targets channel '{ch}' without a recipient; "
                f"delivery will likely fail. Set a recipient (e.g. a chat/channel id)."
            )
        self.scheduler.add_job(
            self._run_config_sop,
            trigger=self._trigger(cron=cron),
            id=job_id,
            args=[sop_name, ch, recipient],
            replace_existing=True,
            misfire_grace_time=_MISFIRE_GRACE,
        )
        self._jobs_meta[job_id] = {
            "job_id": job_id, "cron": cron, "run_at": "",
            "sop_name": sop_name, "prompt": "",
            "channel": ch, "recipient": recipient, "persistent": False,
        }
        logger.info(f"Task scheduled: {job_id} -> {sop_name} ({cron})")
        return job_id

    def schedule(self, *, job_id: str, channel: str = "", recipient: str = "",
                 sop_name: str = "", prompt: str = "",
                 cron: str = "", run_at: str = "", persist: bool = True) -> str:
        """Schedule a runtime job: cron OR one-shot run_at; SOP OR free-text prompt.

        Persisted to SCHEDULE.json so it survives a restart.
        """
        if bool(cron) == bool(run_at):
            raise ValueError("Provide exactly one of cron or run_at.")
        if bool(sop_name) == bool(prompt):
            raise ValueError("Provide exactly one of sop_name or prompt.")
        ch = channel or self.default_channel
        meta = {
            "job_id": job_id, "cron": cron, "run_at": run_at,
            "sop_name": sop_name, "prompt": prompt,
            "channel": ch, "recipient": recipient, "persistent": persist,
        }
        self._register(meta)
        self._jobs_meta[job_id] = meta
        if persist:
            self._persist()
        kind = "cron " + cron if cron else "once @ " + run_at
        logger.info(f"Task scheduled: {job_id} -> {sop_name or 'prompt'} ({kind})")
        return job_id

    def _register(self, meta: dict) -> None:
        self.scheduler.add_job(
            self._run,
            trigger=self._trigger(cron=meta["cron"], run_at=meta["run_at"]),
            id=meta["job_id"],
            args=[meta["job_id"]],
            replace_existing=True,
            misfire_grace_time=_MISFIRE_GRACE,
        )

    # --- execution ---------------------------------------------------------

    async def _run(self, job_id: str) -> None:
        """Dispatch a scheduled job (SOP or prompt) and clean up one-shots."""
        meta = self._jobs_meta.get(job_id)
        if not meta:
            return
        try:
            async with self._run_lock:
                if meta.get("prompt"):
                    await self._run_prompt(meta["prompt"], meta["channel"], meta["recipient"])
                else:
                    await self._run_sop(meta["sop_name"], meta["channel"], meta["recipient"])
        finally:
            # A one-shot (DateTrigger) is spent after it fires — drop it.
            if meta.get("run_at"):
                self._jobs_meta.pop(job_id, None)
                if meta.get("persistent"):
                    self._persist()

    async def _run_config_sop(self, sop_name: str, channel: str, recipient: str = "") -> None:
        """Config-defined cron SOP entrypoint, serialized against every other
        scheduled turn so two jobs firing in the same window can't race the
        shared "scheduler:cron" agent and its session file (review fix)."""
        async with self._run_lock:
            await self._run_sop(sop_name, channel, recipient)

    async def _run_sop(self, sop_name: str, channel: str, recipient: str = "") -> None:
        """Execute a scheduled SOP and send the result to the channel."""
        try:
            agent = self.runtime.get_or_create_agent("scheduler:cron")
            loop = asyncio.get_running_loop()
            # Route a gated tool inside the scheduled SOP through the interrupt
            # resolver against the delivery channel (S6); never silently dropped.
            from aethon.channels.base import InboundMessage

            cron_msg = InboundMessage(
                channel=channel or "scheduler",
                sender_id=recipient or "cron",
                sender_name="Scheduler",
                text="",
            )

            def _invoke(a, p):
                return self.runtime._run_with_interrupts(a, cron_msg, "scheduler:cron", p)

            result = await loop.run_in_executor(
                None, self.sop_runner.run_sop, sop_name, agent, "", _invoke
            )
            await self._deliver(channel, recipient, f"[Scheduled: {sop_name}]\n\n{result}")
            logger.info(f"Scheduled task completed: {sop_name}")
        except Exception as e:
            logger.error(f"Scheduled task error ({sop_name}): {e}")

    async def _run_prompt(self, prompt: str, channel: str, recipient: str = "") -> None:
        """Run a free-text prompt through the runtime and deliver the reply."""
        try:
            from aethon.channels.base import InboundMessage

            msg = InboundMessage(
                channel=channel or "scheduler",
                sender_id=recipient or "cron",
                sender_name="Scheduler",
                text=prompt,
            )
            result = await self.runtime.process(msg, "scheduler:cron")
            await self._deliver(channel, recipient, f"[Scheduled]\n\n{result}")
            logger.info("Scheduled prompt completed")
        except Exception as e:
            logger.error(f"Scheduled prompt error: {e}")

    async def _deliver(self, channel: str, recipient: str, text: str) -> None:
        if not channel:
            return
        from aethon.tools.messaging import get_gateway
        from aethon.channels.base import OutboundMessage

        gw = get_gateway()
        if gw and channel in gw.adapters:
            await gw.adapters[channel].send(
                OutboundMessage(channel=channel, recipient_id=recipient or "default", text=text)
            )

    # --- persistence -------------------------------------------------------

    def _persist(self) -> None:
        """Atomically write the persistent jobs to SCHEDULE.json."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            jobs = [m for m in self._jobs_meta.values() if m.get("persistent")]
            tmp = self._store_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"version": 1, "jobs": jobs}, indent=2))
            os.replace(tmp, self._store_path)
        except Exception as e:
            logger.error(f"Schedule persist error: {e}")

    def load_persisted(self) -> int:
        """Re-register persisted jobs at boot; recover missed one-shots. Returns count."""
        if not self._store_path.exists():
            return 0
        try:
            data = json.loads(self._store_path.read_text())
        except Exception as e:
            logger.error(f"Schedule load error: {e}")
            return 0
        now = datetime.now()
        loaded = 0
        for meta in data.get("jobs", []):
            run_at = meta.get("run_at")
            if run_at:
                try:
                    when = datetime.fromisoformat(run_at)
                except ValueError:
                    continue
                if when <= now:
                    # Missed while AETHON was down — recover it shortly after boot.
                    meta = {**meta, "run_at": (now + timedelta(seconds=5)).isoformat()}
                    logger.info(f"Recovering missed one-shot job '{meta['job_id']}'")
            meta.setdefault("persistent", True)
            self._jobs_meta[meta["job_id"]] = meta
            try:
                self._register(meta)
                loaded += 1
            except Exception as e:
                logger.warning(f"Could not restore job '{meta.get('job_id')}': {e}")
        if loaded:
            logger.info(f"Restored {loaded} persisted scheduled job(s)")
        return loaded

    # --- management --------------------------------------------------------

    def remove_job(self, job_id: str) -> bool:
        try:
            self.scheduler.remove_job(job_id)
        except Exception as e:
            logger.warning(f"Job removal failed ({job_id}): {e}")
            return False
        was_persistent = self._jobs_meta.get(job_id, {}).get("persistent")
        self._jobs_meta.pop(job_id, None)
        if was_persistent:
            self._persist()
        return True

    def list_jobs(self) -> list[dict]:
        result = []
        for job in self.scheduler.get_jobs():
            meta = self._jobs_meta.get(job.id, {})
            result.append({
                "job_id": job.id,
                "sop_name": meta.get("sop_name", "") or ("(prompt)" if meta.get("prompt") else ""),
                "cron": meta.get("cron", "") or (f"once @ {meta.get('run_at')}" if meta.get("run_at") else ""),
                "channel": meta.get("channel", ""),
                "next_run": str(nrt) if (nrt := getattr(job, "next_run_time", None)) else None,
            })
        return result

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# --- Agent Tools ---


@tool
def schedule_task(sop_name: str = "", prompt: str = "", cron_expression: str = "",
                  run_at: str = "", job_id: str = "", channel: str = "",
                  recipient: str = "") -> str:
    """Schedule a task. Survives restarts.

    Provide EITHER a recurring ``cron_expression`` OR a one-shot ``run_at`` (an
    ISO timestamp like ``2026-06-13T15:30``), and EITHER a ``sop_name`` OR a
    free-text ``prompt`` to run.

    Args:
        sop_name: Name of an SOP to run (mutually exclusive with prompt).
        prompt: Free-text instruction to run via the agent (e.g. "dişçiyi ara
            diye hatırlat").
        cron_expression: Cron expression for a recurring task (e.g. "0 9 * * 1-5").
        run_at: ISO timestamp for a one-shot task (e.g. "2026-06-13T15:30").
        job_id: Task id (auto-generated if empty).
        channel: Channel to deliver the result to (default if empty).
        recipient: Destination id on that channel (a chat/channel id); not
            needed for cli/webchat.
    """
    if not _scheduler_instance:
        return "Error: Scheduler not started."
    if not job_id:
        job_id = f"task-{uuid.uuid4().hex[:8]}"
    try:
        _scheduler_instance.schedule(
            job_id=job_id, channel=channel, recipient=recipient,
            sop_name=sop_name, prompt=prompt,
            cron=cron_expression, run_at=run_at,
        )
        when = cron_expression or f"once @ {run_at}"
        return f"Task scheduled: {job_id} -> {sop_name or 'prompt'} ({when})"
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
