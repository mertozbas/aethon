"""Tests for TelemetryHookProvider."""

import time
from unittest.mock import MagicMock

from aethon.agent.hooks.telemetry import TelemetryHookProvider


def _make_before_tool_event(tool_name="shell", tool_id="t1", tool_input=None):
    event = MagicMock()
    event.tool_use = {
        "name": tool_name,
        "toolUseId": tool_id,
        "input": tool_input or {},
    }
    return event


def _make_after_tool_event(tool_name="shell", tool_id="t1", status="success",
                           exception=None):
    event = MagicMock()
    event.tool_use = {
        "name": tool_name,
        "toolUseId": tool_id,
        "input": {},
    }
    event.result = {"status": "error" if status == "error" else "success"}
    event.exception = exception
    return event


def _make_before_model_event():
    event = MagicMock()
    return event


def _make_after_model_event(stop_reason="end_turn", exception=None):
    event = MagicMock()
    if stop_reason:
        event.stop_response = MagicMock()
        event.stop_response.stop_reason = stop_reason
    else:
        event.stop_response = None
    event.exception = exception
    return event


def test_telemetry_creation():
    """TelemetryHookProvider can be created."""
    hook = TelemetryHookProvider(max_history=100)
    assert len(hook.metrics) == 0
    assert hook._timers == {}


def test_telemetry_tool_tracking():
    """Tool calls are tracked with duration."""
    hook = TelemetryHookProvider()
    before = _make_before_tool_event("file_read", "t1")
    hook.before_tool(before)
    time.sleep(0.01)
    after = _make_after_tool_event("file_read", "t1")
    hook.after_tool(after)

    assert len(hook.metrics) == 1
    m = hook.metrics[0]
    assert m["type"] == "tool"
    assert m["name"] == "file_read"
    assert m["status"] == "success"
    assert m["duration"] > 0


def test_telemetry_model_tracking():
    """Model calls are tracked with stop reason."""
    hook = TelemetryHookProvider()
    before = _make_before_model_event()
    hook.before_model(before)
    time.sleep(0.01)
    after = _make_after_model_event("tool_use")
    hook.after_model(after)

    assert len(hook.metrics) == 1
    m = hook.metrics[0]
    assert m["type"] == "model"
    assert m["status"] == "success"
    assert m["extra"]["stop_reason"] == "tool_use"
    assert m["duration"] > 0


def test_telemetry_tool_error_status():
    """Tool error status is tracked."""
    hook = TelemetryHookProvider()
    hook.before_tool(_make_before_tool_event("shell", "t2"))
    hook.after_tool(_make_after_tool_event("shell", "t2", status="error"))

    assert hook.metrics[0]["status"] == "error"


def test_telemetry_tool_exception_status():
    """Tool exception status is tracked."""
    hook = TelemetryHookProvider()
    hook.before_tool(_make_before_tool_event("shell", "t3"))
    hook.after_tool(
        _make_after_tool_event("shell", "t3", exception=RuntimeError("fail"))
    )

    assert hook.metrics[0]["status"] == "exception"


def test_telemetry_model_error():
    """Model error status is tracked."""
    hook = TelemetryHookProvider()
    hook.before_model(_make_before_model_event())
    hook.after_model(_make_after_model_event(exception=RuntimeError("timeout")))

    assert hook.metrics[0]["status"] == "error"


def test_telemetry_model_no_stop_response():
    """Model call with no stop_response handled gracefully."""
    hook = TelemetryHookProvider()
    hook.before_model(_make_before_model_event())
    hook.after_model(_make_after_model_event(stop_reason=None))

    assert hook.metrics[0]["extra"]["stop_reason"] == ""


def test_telemetry_max_history():
    """Metrics bounded by max_history."""
    hook = TelemetryHookProvider(max_history=5)
    for i in range(10):
        hook.before_tool(_make_before_tool_event("shell", f"t{i}"))
        hook.after_tool(_make_after_tool_event("shell", f"t{i}"))

    assert len(hook.metrics) == 5


def test_telemetry_get_metrics_limit():
    """get_metrics returns limited subset."""
    hook = TelemetryHookProvider()
    for i in range(10):
        hook.before_tool(_make_before_tool_event("shell", f"t{i}"))
        hook.after_tool(_make_after_tool_event("shell", f"t{i}"))

    result = hook.get_metrics(limit=3)
    assert len(result) == 3


def test_telemetry_get_summary():
    """get_summary returns correct aggregation."""
    hook = TelemetryHookProvider()
    # 2 tool calls
    hook.before_tool(_make_before_tool_event("shell", "t1"))
    hook.after_tool(_make_after_tool_event("shell", "t1"))
    hook.before_tool(_make_before_tool_event("file_read", "t2"))
    hook.after_tool(_make_after_tool_event("file_read", "t2", status="error"))
    # 1 model call
    hook.before_model(_make_before_model_event())
    hook.after_model(_make_after_model_event("end_turn"))

    summary = hook.get_summary()
    assert summary["total_tool_calls"] == 2
    assert summary["total_model_calls"] == 1
    assert summary["error_count"] == 1
    assert summary["avg_tool_duration"] >= 0
    assert summary["avg_model_duration"] >= 0


def test_telemetry_register_hooks():
    """Hook can register with registry."""
    hook = TelemetryHookProvider()
    registry = MagicMock()
    hook.register_hooks(registry)
    assert registry.add_callback.call_count == 4


def test_telemetry_concurrent_tool_tracking():
    """Multiple concurrent tool calls tracked independently."""
    hook = TelemetryHookProvider()
    hook.before_tool(_make_before_tool_event("shell", "t1"))
    hook.before_tool(_make_before_tool_event("file_read", "t2"))
    time.sleep(0.01)
    hook.after_tool(_make_after_tool_event("file_read", "t2"))
    hook.after_tool(_make_after_tool_event("shell", "t1"))

    assert len(hook.metrics) == 2
    assert hook.metrics[0]["name"] == "file_read"
    assert hook.metrics[1]["name"] == "shell"


# --- R17: repeated-tool-failure surfacer ---


def test_repeated_failures_surface_to_agent():
    """R17: the third failure in the window injects a loud notice into the
    tool result instead of only logging."""
    from aethon.agent.hooks.telemetry import TelemetryHookProvider

    hook = TelemetryHookProvider()
    last_event = None
    for _ in range(TelemetryHookProvider.FAILURE_THRESHOLD):
        last_event = _make_after_tool_event(status="error")
        last_event.result["content"] = []
        hook.after_tool(last_event)

    texts = [b.get("text", "") for b in last_event.result["content"]]
    assert any("[Reliability]" in t for t in texts)
    # Counter resets after surfacing — the next single failure is quiet.
    quiet = _make_after_tool_event(status="error")
    quiet.result["content"] = []
    hook.after_tool(quiet)
    assert quiet.result["content"] == []


def test_successes_do_not_accumulate():
    from aethon.agent.hooks.telemetry import TelemetryHookProvider

    hook = TelemetryHookProvider()
    for _ in range(5):
        ev = _make_after_tool_event(status="success")
        ev.result["content"] = []
        hook.after_tool(ev)
        assert ev.result["content"] == []
