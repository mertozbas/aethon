"""Ambient / autonomous mode.

A background asyncio task that, when enabled and started, periodically prompts the
agent to do proactive (ambient) or self-directed (autonomous) work during idle
time. Fully opt-in and runtime-toggleable; dormant by default.

Concurrency: ambient iterations run on a dedicated session, so they never share
an agent instance with live user sessions. ``runtime.process()`` offloads the
blocking agent call to a thread executor, so the loop never starves real message
handling. Completion signals are checked server-side (immune to prompt injection).
"""

import asyncio
import logging
import time
from typing import Optional

from aethon.channels.base import InboundMessage

logger = logging.getLogger("aethon.ambient")

_AMBIENT_SESSION = "ambient:local"
_MAX_RESULTS_HISTORY = 50  # cap pending results so an undrained autonomous run stays bounded

# R12: ambient work is bound to the task ledger — the loop advances the
# user's recorded backlog instead of inventing plausible-sounding work.
_AMBIENT_PROMPTS = [
    "You have idle time. Check the task ledger (manage_tasks action='list'): "
    "pick the highest-priority task with status open or in_progress and make "
    "concrete progress on it, updating the ledger as you go. Do NOT invent "
    "work that is not in the ledger. If no open task exists, reply with "
    "exactly {signal} and stop.",
    "Idle cycle: continue the most important open ledger task "
    "(manage_tasks action='list'). Record progress/evidence on the task. "
    "If the ledger has no open tasks, reply with exactly {signal}.",
    "Idle cycle: review open ledger tasks and finish the smallest one you can "
    "complete now — mark it done with verification evidence. If none are "
    "open, reply with exactly {signal}.",
]


class AmbientModeManager:
    """Manage an opt-in background loop for proactive/autonomous work."""

    def __init__(self, runtime, config, event_bus=None):
        self.runtime = runtime
        self.config = getattr(config, "ambient", config)
        self.event_bus = event_bus
        self.running = False
        self.autonomous = False
        self.ambient_iterations = 0
        self.ambient_results_history: list = []
        self.last_query: Optional[str] = None
        self.last_response: Optional[str] = None
        self.last_interaction: float = time.time()
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._interrupted = False

    def set_loop(self, loop) -> None:
        self._loop = loop

    # ---- thread-safe request methods (called from @tool in the executor) ----

    def request_start(self, autonomous: bool = False) -> str:
        if self.running:
            return "Ambient mode is already running."
        if self._loop is None:
            return "Ambient mode is unavailable (no event loop bound)."
        asyncio.run_coroutine_threadsafe(self.start(autonomous), self._loop)
        return f"Ambient mode starting ({'autonomous' if autonomous else 'ambient'})."

    def request_stop(self) -> str:
        if not self.running:
            return "Ambient mode is not running."
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.stop(), self._loop)
        else:
            self.running = False
        return "Ambient mode stopping."

    def status(self) -> dict:
        return {
            "running": self.running,
            "autonomous": self.autonomous,
            "iterations": self.ambient_iterations,
            "pending_results": len(self.ambient_results_history),
            "last_interaction_age_s": round(time.time() - self.last_interaction, 1),
        }

    # ---- lifecycle ----

    async def start(self, autonomous: bool = False) -> None:
        if self.running:
            return
        self.running = True
        self.autonomous = autonomous
        self.ambient_iterations = 0
        self._interrupted = False
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        self._task = asyncio.create_task(self._ambient_loop())
        logger.info(f"Ambient mode started (autonomous={autonomous})")

    async def stop(self) -> None:
        # NOTE: if cancellation lands while an iteration is awaiting
        # runtime.process() (offloaded to a thread executor), that in-flight call
        # finishes in the background and its result is discarded — the loop does
        # not continue.
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._task = None
        logger.info("Ambient mode stopped")

    def interrupt(self) -> None:
        self._interrupted = True

    def record_interaction(self, query: str, result: str) -> None:
        """Called after each real user message — resets the idle clock."""
        self.last_query = query
        self.last_response = result
        self.last_interaction = time.time()
        if not self.autonomous:
            self.ambient_iterations = 0

    def get_and_clear_result(self) -> list:
        results = list(self.ambient_results_history)
        self.ambient_results_history.clear()
        return results

    # ---- internals ----

    def _max_iterations(self) -> int:
        return (
            self.config.autonomous_max_iterations
            if self.autonomous
            else self.config.max_iterations
        )

    def _cooldown(self) -> float:
        return (
            self.config.autonomous_cooldown_seconds
            if self.autonomous
            else self.config.cooldown_seconds
        )

    def _build_ambient_prompt(self) -> str:
        idx = self.ambient_iterations % len(_AMBIENT_PROMPTS)
        return _AMBIENT_PROMPTS[idx].format(signal=self.config.completion_signal)

    def _check_completion_signal(self, text: str) -> bool:
        """True when the agent signals completion AND the ledger agrees.

        The free-text signal alone is trivially emittable (R12); when a task
        ledger is available, completion also requires that no open task
        remains, so 'done' is a verified state rather than a substring.
        """
        if not (bool(text) and self.config.completion_signal in text):
            return False
        ledger = getattr(self.runtime, "_task_ledger", None)
        if ledger is None:
            return True
        try:
            remaining = ledger.open_tasks()
        except Exception as e:
            logger.warning(f"Ambient ledger check failed: {e}")
            return True
        if remaining:
            logger.info(
                f"Ambient completion signal ignored: {len(remaining)} open "
                f"ledger task(s) remain"
            )
            return False
        return True

    async def _ambient_loop(self) -> None:
        try:
            while self.running:
                await asyncio.sleep(self._cooldown())
                if not self.running:
                    break
                if self._interrupted:
                    self._interrupted = False
                    continue
                # Idle gate (non-autonomous): only act when genuinely idle.
                if not self.autonomous:
                    if time.time() - self.last_interaction < self.config.idle_threshold_seconds:
                        continue
                if self.ambient_iterations >= self._max_iterations():
                    logger.info("Ambient mode reached its iteration cap; stopping")
                    self.running = False
                    break
                self.ambient_iterations += 1
                try:
                    msg = InboundMessage(
                        channel="ambient",
                        sender_id="system",
                        sender_name="ambient",
                        text=self._build_ambient_prompt(),
                    )
                    result = await self.runtime.process(msg, _AMBIENT_SESSION)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    result = f"(ambient iteration error: {e})"
                entry = {
                    "iteration": self.ambient_iterations,
                    "result": (result or "")[:1000],
                    "timestamp": time.time(),
                }
                self.ambient_results_history.append(entry)
                if len(self.ambient_results_history) > _MAX_RESULTS_HISTORY:
                    self.ambient_results_history = self.ambient_results_history[
                        -_MAX_RESULTS_HISTORY:
                    ]
                if self.event_bus:
                    try:
                        self.event_bus.emit("ambient", {**entry, "status": "running"})
                    except Exception:
                        pass
                if self._check_completion_signal(result or ""):
                    logger.info("Ambient completion signal received; stopping")
                    self.autonomous = False
                    self.running = False
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            self._task = None  # keep the running ⟺ _task invariant on all exit paths
            if self.event_bus:
                try:
                    self.event_bus.emit(
                        "ambient",
                        {"status": "stopped", "iterations": self.ambient_iterations},
                    )
                except Exception:
                    pass
