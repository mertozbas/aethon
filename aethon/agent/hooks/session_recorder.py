"""Session recorder hook.

Drives a :class:`SessionRecorder` from the Strands hook chain — recording tool
calls/results and model responses, and taking a state snapshot after each agent
invocation. The gateway starts recording on boot and exports a ZIP on shutdown.
Read-only with respect to agent behavior (it only observes). Opt-in via
``session_recorder.enabled``.
"""

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import (
    AfterInvocationEvent,
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeToolCallEvent,
)

from aethon.agent.session_recording import EventBuffer, SessionRecorder

logger = logging.getLogger("aethon.session_recorder")


class SessionRecorderHookProvider(HookProvider):
    """Observe the agent and record events/snapshots for later replay."""

    def __init__(self, config=None, recordings_dir: str | None = None):
        self.config = config
        max_events = getattr(config, "max_events", 10000) if config else 10000
        self.recorder = SessionRecorder()
        self.recorder.event_buffer = EventBuffer(max_events=max_events)
        if config and getattr(config, "redact_patterns", None):
            self.recorder.REDACT_PATTERNS = list(config.redact_patterns)
        self.recordings_dir = recordings_dir
        self._agent = None  # most recent agent seen, for snapshots

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self._on_before_tool)
        registry.add_callback(AfterToolCallEvent, self._on_after_tool)
        registry.add_callback(AfterModelCallEvent, self._on_after_model)
        registry.add_callback(AfterInvocationEvent, self._on_after_invocation)

    # ---- event callbacks (never raise into the agent) --------------------

    def _on_before_tool(self, event) -> None:
        try:
            self._agent = getattr(event, "agent", None) or self._agent
            tu = event.tool_use or {}
            self.recorder.record_tool_call(
                tu.get("name", ""), tu.get("input", {}) or {}, tu.get("toolUseId")
            )
        except Exception:
            pass

    def _on_after_tool(self, event) -> None:
        try:
            tu = event.tool_use or {}
            self.recorder.record_tool_result(
                tu.get("name", ""), event.result, trace_id=tu.get("toolUseId")
            )
        except Exception:
            pass

    def _on_after_model(self, event) -> None:
        try:
            self._agent = getattr(event, "agent", None) or self._agent
            self.recorder.record_sys_event("model.response", {})
        except Exception:
            pass

    def _on_after_invocation(self, event) -> None:
        try:
            agent = getattr(event, "agent", None) or self._agent
            lq, lr = self._last_exchange(agent)
            self.recorder.snapshot(
                agent=agent, description="post-invocation", last_query=lq, last_result=lr
            )
        except Exception:
            pass

    @staticmethod
    def _last_exchange(agent) -> tuple[str, str]:
        """Best-effort extraction of the last user query + assistant result."""
        last_query = last_result = ""
        try:
            for msg in reversed(getattr(agent, "messages", []) or []):
                role = msg.get("role") if isinstance(msg, dict) else None
                text = ""
                content = msg.get("content") if isinstance(msg, dict) else None
                if isinstance(content, list):
                    text = " ".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    ).strip()
                elif isinstance(content, str):
                    text = content
                if role == "assistant" and not last_result:
                    last_result = text
                elif role == "user" and not last_query:
                    last_query = text
                if last_query and last_result:
                    break
        except Exception:
            pass
        return last_query, last_result

    # ---- lifecycle (called by the gateway) -------------------------------

    def start_recording(self, session_id: str | None = None) -> None:
        if session_id:
            self.recorder.session_id = session_id
        # AETHON drives recording through this provider, so no OS-level monkeypatching.
        self.recorder.start(install_hooks=False)

    def snapshot(self, **kwargs) -> None:
        self.recorder.snapshot(agent=self._agent, **kwargs)

    def stop_and_export(self) -> str | None:
        if not self.recorder.recording:
            return None
        self.recorder.stop()
        output_path = None
        if self.recordings_dir:
            from pathlib import Path

            d = Path(self.recordings_dir).expanduser()
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            output_path = str(d / f"{self.recorder.session_id}.zip")
        try:
            return self.recorder.export(output_path)
        except Exception as e:
            logger.warning(f"Session export failed: {e}")
            return None
