"""Telemetry hook provider.

Tracks tool and model call metrics: duration, status, stop reason.
Stores metrics in a bounded deque for dashboard consumption.
"""

import time
import logging
from collections import deque
from datetime import datetime
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    BeforeToolCallEvent, AfterToolCallEvent,
    BeforeModelCallEvent, AfterModelCallEvent,
)


logger = logging.getLogger("aethon.telemetry")


class TelemetryHookProvider(HookProvider):
    """Track and log tool and model call metrics."""

    # R17: a tool failing this many times within the window is surfaced to the
    # conversation (injected into the tool result) instead of only logged —
    # the agent must report it to the user rather than silently work around it.
    FAILURE_THRESHOLD = 3
    FAILURE_WINDOW_SECONDS = 600

    def __init__(self, max_history: int = 10000, event_bus=None):
        self.metrics: deque = deque(maxlen=max_history)
        self._timers: dict[str, float] = {}
        self._event_bus = event_bus
        self._failures: dict[str, list[float]] = {}

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)
        registry.add_callback(BeforeModelCallEvent, self.before_model)
        registry.add_callback(AfterModelCallEvent, self.after_model)

    @staticmethod
    def _identity(event) -> dict:
        """Agent identity for the dashboard pixel office (maps events to a character)."""
        agent = getattr(event, "agent", None)
        return {
            "session_id": getattr(agent, "__aethon_session__", None),
            "agent_id": getattr(agent, "agent_id", "main"),
            "agent_name": getattr(agent, "name", "AETHON"),
        }

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        tool_id = event.tool_use.get("toolUseId", "unknown")
        self._timers[f"tool:{tool_id}"] = time.monotonic()

        # Emit tool_start event for dashboard
        if self._event_bus:
            tool_name = event.tool_use.get("name", "unknown")
            self._event_bus.emit("agents", {
                "event": "tool_start",
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat(),
                **self._identity(event),
            })

    def after_tool(self, event: AfterToolCallEvent) -> None:
        tool_id = event.tool_use.get("toolUseId", "unknown")
        start = self._timers.pop(f"tool:{tool_id}", time.monotonic())
        duration = time.monotonic() - start

        status = "success"
        if event.exception:
            status = "exception"
        elif event.result.get("status") == "error":
            status = "error"

        record = {
            "type": "tool",
            "name": event.tool_use["name"],
            "duration": round(duration, 4),
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "extra": {},
        }
        self.metrics.append(record)
        logger.info(f"TOOL: {record['name']} | {duration:.2f}s | {status}")
        # Surface the actual error so failures are diagnosable (not just "exception").
        if event.exception is not None:
            logger.warning(
                f"TOOL EXCEPTION: {record['name']} -> "
                f"{type(event.exception).__name__}: {event.exception}"
            )
        if status != "success":
            self._track_repeated_failure(event, record["name"])

        # Emit to dashboard event bus
        if self._event_bus:
            self._event_bus.emit("telemetry", record)
            self._event_bus.emit("agents", {
                "event": "tool_end",
                "tool_name": record["name"],
                "status": status,
                "duration": record["duration"],
                "timestamp": record["timestamp"],
                **self._identity(event),
            })

    def _track_repeated_failure(self, event: AfterToolCallEvent, name: str) -> None:
        """R17: surface a recurring tool failure instead of only logging it.

        Keeps a per-tool failure timestamp window; on threshold, injects a
        loud notice into the tool result (the agent's Operating Rules require
        reporting it to the user), emits a reliability event for the
        dashboard, and logs at ERROR.
        """
        now = time.monotonic()
        window = [
            t for t in self._failures.get(name, [])
            if now - t < self.FAILURE_WINDOW_SECONDS
        ]
        window.append(now)
        self._failures[name] = window
        if len(window) < self.FAILURE_THRESHOLD:
            return
        self._failures[name] = []  # reset so the notice fires once per streak

        notice = (
            f"[Reliability] The '{name}' tool has failed "
            f"{self.FAILURE_THRESHOLD}+ times in the last "
            f"{self.FAILURE_WINDOW_SECONDS // 60} minutes. This looks like a "
            f"broken tool or environment — report it to the user now instead "
            f"of working around it."
        )
        logger.error(f"REPEATED TOOL FAILURE: {name} — surfacing to the agent")
        try:
            existing = event.result.get("content", []) or []
            existing.append({"text": "\n" + notice})
            event.result["content"] = existing
        except Exception as e:
            logger.warning(f"Failure notice injection failed: {e}")
        if self._event_bus:
            self._event_bus.emit("reliability", {
                "event": "repeated_tool_failure",
                "tool_name": name,
                "threshold": self.FAILURE_THRESHOLD,
                "timestamp": datetime.now().isoformat(),
            })

    def before_model(self, event: BeforeModelCallEvent) -> None:
        self._timers["model"] = time.monotonic()

    def after_model(self, event: AfterModelCallEvent) -> None:
        start = self._timers.pop("model", time.monotonic())
        duration = time.monotonic() - start

        stop_reason = ""
        if event.stop_response:
            stop_reason = getattr(event.stop_response, "stop_reason", "")

        status = "error" if event.exception else "success"

        record = {
            "type": "model",
            "name": "model_call",
            "duration": round(duration, 4),
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "extra": {"stop_reason": stop_reason},
        }
        self.metrics.append(record)
        logger.info(f"MODEL: {duration:.2f}s | stop={stop_reason}")

        # Emit to dashboard event bus
        if self._event_bus:
            self._event_bus.emit("telemetry", record)
            self._event_bus.emit("agents", {
                "event": "model",
                "status": status,
                "duration": record["duration"],
                "timestamp": record["timestamp"],
                **self._identity(event),
            })

    def get_metrics(self, limit: int = 100) -> list[dict]:
        """Return recent metrics (most recent last)."""
        return list(self.metrics)[-limit:]

    def get_summary(self) -> dict:
        """Return aggregated summary of all metrics."""
        tool_calls = [m for m in self.metrics if m["type"] == "tool"]
        model_calls = [m for m in self.metrics if m["type"] == "model"]
        return {
            "total_tool_calls": len(tool_calls),
            "total_model_calls": len(model_calls),
            "avg_tool_duration": (
                round(sum(m["duration"] for m in tool_calls) / len(tool_calls), 4)
                if tool_calls else 0
            ),
            "avg_model_duration": (
                round(sum(m["duration"] for m in model_calls) / len(model_calls), 4)
                if model_calls else 0
            ),
            "error_count": sum(
                1 for m in self.metrics if m["status"] != "success"
            ),
        }
