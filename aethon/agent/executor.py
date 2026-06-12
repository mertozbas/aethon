"""Project executor (Phase 10 C3).

The bounded autonomous loop. Given a planned project (a parent task with child
tasks in the ledger), work it toward completion: pick the most-urgent task whose
dependencies are satisfied, drive one agent turn on it, and advance when the
ledger shows progress. The loop trusts the LEDGER, never the agent's prose — a
task counts as done only when it is marked done (which the ledger requires
evidence for), so the stop condition is a verified state.

Runaway prevention is the point (the design's priority red-team target): the run
is bounded by an iteration cap, the E0 budget ceiling re-checked BETWEEN tasks
(the per-turn gate alone can't bound a multi-task run), and a per-task attempt
limit so a task the agent can't finish can't spin forever.
"""

from __future__ import annotations

import asyncio
import logging
import re

from aethon.channels.base import InboundMessage

logger = logging.getLogger("aethon.executor")

# A hung adapter.send must not stall the executor — bound the delivery wait.
_DELIVER_TIMEOUT = 10.0


def _flat(value) -> str:
    """Collapse whitespace — receipt/pulse text reaches a channel, and embedded
    newlines from tool output could fabricate message structure."""
    return re.sub(r"\s+", " ", str(value)).strip()


class ProjectExecutor:
    """Drives a single project's tasks to completion, bounded on every axis."""

    def __init__(self, runtime):
        self.runtime = runtime

    def _task_prompt(self, task: dict) -> str:
        tid = task.get("id", "")
        title = task.get("title", "")
        prompt = f"Aktif projedeki sıradaki görev [{tid}]: {title}.\n"
        crit = task.get("acceptance_criteria", "")
        if crit:
            prompt += f"Tamamlanma ölçütü: {crit}.\n"
        prompt += (
            f"Bu görevi tamamla. Bittiğinde manage_tasks ile action=complete, "
            f"task_id={tid} ve doğrulama kanıtını (evidence) yazarak ledger'da "
            f"işaretle."
        )
        return prompt

    async def run(self, parent_id: str) -> dict:
        """Work the project ``parent_id`` until it is complete, blocked, or a
        bound is hit. Returns a structured summary with the stop reason
        (complete / partial / blocked / cap / budget).
        """
        led = self.runtime._task_ledger
        cfg = self.runtime.config.core_loop
        meter = getattr(self.runtime, "token_meter", None)
        max_iter = max(1, int(getattr(cfg, "executor_max_iterations", 20)))
        max_attempts = max(1, int(getattr(cfg, "executor_max_task_attempts", 3)))
        stop_on_budget = getattr(cfg, "executor_stop_on_budget", True)
        pulse_enabled = getattr(cfg, "pulse_enabled", True)
        pulse_n = max(1, int(getattr(cfg, "pulse_every_n_tasks", 3)))
        session_id = f"executor:{parent_id}"

        iterations = 0
        reason = None
        # Tasks already done when the run starts (e.g. a resume) must not pulse.
        seen_done = {
            k["id"] for k in led.children(parent_id) if k.get("status") == "done"
        }
        pulse_pending = 0

        while iterations < max_iter:
            # Budget gate BETWEEN tasks — the per-turn gate in process() can't
            # bound a whole multi-task run, so re-check here before each pick.
            if stop_on_budget and meter is not None and meter.over_budget():
                reason = "budget"
                break

            available = led.available_tasks(parent_id)
            if not available:
                # Decide why from the durable ledger state.
                kids = led.children(parent_id)
                if not kids:
                    reason = "empty"       # nothing planned — never claim success
                elif any(k.get("status") in ("open", "in_progress") for k in kids):
                    reason = "blocked"     # open tasks with unsatisfiable deps
                elif any(k.get("status") == "dropped" for k in kids):
                    reason = "partial"     # finished, but some tasks were dropped
                else:
                    reason = "complete"
                break

            task = available[0]
            tid = task["id"]
            # Per-task attempt limit, read from the LEDGER so it survives
            # re-invocation (a new executor each ambient tick) and process
            # restarts — an in-memory counter reset on every run was the hole
            # that let a stuck task be retried far past its limit. Give up
            # durably (drop it) so it leaves available_tasks for good.
            attempts = int(task.get("executor_attempts", 0) or 0)
            if attempts >= max_attempts:
                led.update(tid, status="dropped")
                logger.warning(
                    f"Executor dropped {tid} after {max_attempts} attempts (stuck)."
                )
                continue

            # A concurrent user turn may have just finished this task between the
            # available_tasks read and here — don't revert a 'done' task.
            current = led.get(tid)
            if current is None or current.get("status") == "done":
                continue

            iterations += 1
            led.update(tid, status="in_progress", executor_attempts=attempts + 1)
            logger.info(
                f"Executor: working {tid} (iteration {iterations}/{max_iter}, "
                f"attempt {attempts + 1}/{max_attempts})."
            )
            msg = InboundMessage(
                channel="executor", sender_id="C3", sender_name="Executor",
                text=self._task_prompt(task),
            )
            try:
                await self.runtime.process(msg, session_id)
            except Exception as e:
                logger.warning(
                    f"Executor turn failed on {tid}: {type(e).__name__}: {e}"
                )
            # Verified stop: the next iteration re-queries the ledger. A task the
            # agent didn't actually mark done (with evidence) stays available and
            # burns a durable attempt — it cannot be silently counted as complete.

            # C4 pulse: count NEW completions; pulse every N (silenceable).
            if pulse_enabled:
                done_now = {
                    k["id"] for k in led.children(parent_id)
                    if k.get("status") == "done"
                }
                pulse_pending += len(done_now - seen_done)
                seen_done = done_now
                if pulse_pending >= pulse_n:
                    pulse_pending = 0
                    await self._deliver_pulse(led, parent_id)

        if reason is None:           # exited via the iteration cap
            reason = "cap"
        summary = self._summary(led, parent_id, reason, iterations)
        await self._deliver_receipt(led, parent_id, summary)
        return summary

    def _summary(self, led, parent_id, reason, iterations) -> dict:
        kids = led.children(parent_id)
        done = [k["id"] for k in kids if k.get("status") == "done"]
        dropped = [k["id"] for k in kids if k.get("status") == "dropped"]
        remaining = [k["id"] for k in kids if k.get("status") in ("open", "in_progress")]
        summary = {
            "project_id": parent_id,
            "reason": reason,
            "iterations": iterations,
            "done": done,
            "dropped": dropped,
            "remaining": remaining,
        }
        logger.info(
            f"Executor finished project {parent_id}: {reason} "
            f"({len(done)} done, {len(dropped)} dropped, {len(remaining)} "
            f"remaining, {iterations} iterations)."
        )
        return summary

    # ---- C4: pulse + proof-of-work receipt ----

    def _build_pulse(self, led, parent_id) -> str:
        kids = led.children(parent_id)
        total = len(kids)
        done = sum(1 for k in kids if k.get("status") == "done")
        line = f"⏳ {done}/{total} görev bitti"
        cur = next((k for k in kids if k.get("status") == "in_progress"), None)
        if cur:
            line += f" · şu an: {_flat(cur.get('title', ''))}"
        return line

    def _build_receipt(self, led, parent_id, summary) -> str:
        """An HONEST proof-of-work receipt: per-task status with the real
        evidence the ledger captured (never a bare 'done', never fabricated)."""
        parent = led.get(parent_id) or {}
        title = _flat(parent.get("title", "")) or parent_id
        kids = led.children(parent_id)
        done = [k for k in kids if k.get("status") == "done"]
        dropped = [k for k in kids if k.get("status") == "dropped"]
        headers = {
            "complete": f"✅ Bitti — '{title}'. İşte kanıtı:",
            "partial": f"⚠️ Kısmen bitti — '{title}' ({len(dropped)} görev tamamlanamadı):",
            "blocked": f"⛔ Takıldı — '{title}' (bağımlılıklar çözülemedi):",
            "cap": f"⏸️ Durduruldu — '{title}' (iterasyon sınırı):",
            "budget": f"⏸️ Durduruldu — '{title}' (token bütçesi aşıldı):",
            "empty": f"ℹ️ '{title}' — görev yok.",
        }
        lines = [headers.get(summary["reason"], f"'{title}':")]
        for k in done:
            ev = _flat(k.get("evidence", ""))
            # Mark truncation explicitly — a silently cut tail could hide a
            # FAIL/error at the end of the evidence (review fix).
            ev = (ev[:300] + " …(kırpıldı)") if len(ev) > 300 else (ev or "(kanıt yok)")
            lines.append(f"- ✓ [{k['id']}] {_flat(k.get('title', ''))} — kanıt: {ev}")
        for k in dropped:
            lines.append(f"- ✗ [{k['id']}] {_flat(k.get('title', ''))} (tamamlanamadı)")
        return "\n".join(lines)

    async def _deliver_pulse(self, led, parent_id) -> None:
        parent = led.get(parent_id) or {}
        channel = parent.get("origin_channel", "")
        if channel:
            await self._deliver(
                channel, parent.get("origin_recipient", ""),
                self._build_pulse(led, parent_id),
            )

    async def _deliver_receipt(self, led, parent_id, summary) -> None:
        if not getattr(self.runtime.config.core_loop, "receipt_enabled", True):
            return
        parent = led.get(parent_id) or {}
        channel = parent.get("origin_channel", "")
        if channel:
            await self._deliver(
                channel, parent.get("origin_recipient", ""),
                self._build_receipt(led, parent_id, summary),
            )

    async def _deliver(self, channel: str, recipient: str, text: str) -> None:
        """Best-effort delivery to a user channel via the gateway. Fail loud
        (warn) rather than silently dropping when no gateway/adapter is up."""
        from aethon.channels.base import OutboundMessage
        from aethon.tools.messaging import get_gateway

        gw = get_gateway()
        if not gw or channel not in getattr(gw, "adapters", {}):
            logger.warning(
                f"Executor could not deliver to {channel!r} "
                f"(no gateway/adapter up); message dropped."
            )
            return
        try:
            await asyncio.wait_for(
                gw.adapters[channel].send(
                    OutboundMessage(
                        channel=channel, recipient_id=recipient or "default", text=text
                    )
                ),
                timeout=_DELIVER_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Executor delivery to {channel} timed out after "
                f"{_DELIVER_TIMEOUT}s; message dropped."
            )
        except Exception as e:
            logger.warning(
                f"Executor delivery to {channel} failed: {type(e).__name__}: {e}"
            )
