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

    def __init__(self, max_history: int = 10000, event_bus=None):
        self.metrics: deque = deque(maxlen=max_history)
        self._timers: dict[str, float] = {}
        self._event_bus = event_bus

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)
        registry.add_callback(BeforeModelCallEvent, self.before_model)
        registry.add_callback(AfterModelCallEvent, self.after_model)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        tool_id = event.tool_use.get("toolUseId", "unknown")
        self._timers[f"tool:{tool_id}"] = time.monotonic()

        # Emit tool_start event for dashboard
        if self._event_bus:
            tool_name = event.tool_use.get("name", "unknown")
            self._event_bus.emit("agents", {
                "event": "tool_start",
                "agent_name": "AETHON",
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat(),
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

        # Emit to dashboard event bus
        if self._event_bus:
            self._event_bus.emit("telemetry", record)
            self._event_bus.emit("agents", {
                "event": "tool_end",
                "agent_name": "AETHON",
                "tool_name": record["name"],
                "status": status,
                "duration": record["duration"],
                "timestamp": record["timestamp"],
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
