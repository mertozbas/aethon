"""Session recording core — event buffer, recorder, and snapshot dataclasses.

Captures a session's tool/agent events and periodic state snapshots, and exports
them to a ZIP (events.jsonl + snapshots.json + metadata.json + session.pkl) for
later replay via ``aethon.agent.replay.LoadedSession``.
"""

import builtins
import json
import logging
import os
import platform
import socket
import sys
import tempfile
import threading
import time
import zipfile
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:  # better serialization when available, else stdlib pickle
    import dill as serializer

    SERIALIZER_NAME = "dill"
except ImportError:
    import pickle as serializer

    SERIALIZER_NAME = "pickle"

logger = logging.getLogger("aethon.session_recorder")

# Default export directory (overridden by the gateway via config.paths.recordings).
RECORDING_DIR = Path(tempfile.gettempdir()) / "aethon" / "recordings"
try:
    RECORDING_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

@dataclass
class RecordedEvent:
    """A single recorded event in the session timeline."""

    timestamp_ns: int
    layer: str  # "sys", "tool", "agent"
    event_type: str
    data: Dict[str, Any]
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionSnapshot:
    """A snapshot of agent state at a point in time."""

    timestamp: float
    snapshot_id: int
    agent_messages_count: int
    tools_loaded: List[str]
    system_prompt_hash: str
    env_vars_redacted: Dict[str, str]
    cwd: str
    events_since_last: int
    # NEW: Store actual conversation state for true resume capability
    agent_messages: List[Dict[str, Any]] = field(default_factory=list)
    system_prompt: str = ""
    last_query: str = ""
    last_result: str = ""
    model_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EventBuffer:
    """Ring buffer for recording events across all layers."""

    def __init__(self, max_events: int = 10000):
        self.events: deque = deque(maxlen=max_events)
        self.lock = threading.Lock()
        self._event_count = 0

    def record(
        self, layer: str, event_type: str, data: Dict[str, Any], trace_id: str = None
    ):
        """Record an event to the buffer."""
        event = RecordedEvent(
            timestamp_ns=time.time_ns(),
            layer=layer,
            event_type=event_type,
            data=data,
            trace_id=trace_id,
        )
        with self.lock:
            self.events.append(event)
            self._event_count += 1

    def get_recent(self, seconds: float = 5.0) -> List[RecordedEvent]:
        """Get events from the last N seconds."""
        cutoff = time.time_ns() - int(seconds * 1e9)
        with self.lock:
            return [e for e in self.events if e.timestamp_ns > cutoff]

    def get_recent_context(self, seconds: float = 5.0, max_events: int = 20) -> str:
        """Get recent events formatted for system prompt injection."""
        recent = self.get_recent(seconds)[-max_events:]
        if not recent:
            return ""

        lines = ["## 🎬 Recent System Events:"]
        for event in recent:
            ts = datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime(
                "%H:%M:%S.%f"
            )[:-3]
            lines.append(
                f"- [{ts}] [{event.layer}] {event.event_type}: {json.dumps(event.data)[:200]}"
            )
        return "\n".join(lines)

    def get_all(self) -> List[RecordedEvent]:
        """Get all events in the buffer."""
        with self.lock:
            return list(self.events)

    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.events.clear()
            self._event_count = 0

    @property
    def count(self) -> int:
        return self._event_count


class SessionRecorder:
    """Records AETHON sessions for replay.

    Captures three layers:
    - sys: OS-level events (file I/O, network)
    - tool: Agent tool calls and results
    - agent: Messages, decisions, state changes

    Exports to a ZIP containing:
    - session.pkl: Serialized snapshots (dill/pickle)
    - events.jsonl: All events in JSON Lines format
    - metadata.json: Session info
    """

    # Keys to redact from environment variables
    REDACT_PATTERNS = ["KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "AUTH"]

    def __init__(self, session_id: str = None):
        self.session_id = (
            session_id or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.event_buffer = EventBuffer()
        self.snapshots: List[SessionSnapshot] = []
        self.recording = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self._snapshot_counter = 0
        self._original_open = None
        self._original_requests_get = None
        self._hooks_installed = False
        self.metadata: Dict[str, Any] = {}

    def start(self, install_hooks: bool = True):
        """Start recording the session."""
        if self.recording:
            logger.warning("Session recording already active")
            return

        self.recording = True
        self.start_time = time.time()
        self.metadata = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "python_version": sys.version,
            "serializer": SERIALIZER_NAME,
        }

        logger.info(f"🎬 Session recording started: {self.session_id}")
        print(f"🎬 Recording session: {self.session_id}")

        # Record start event
        self.event_buffer.record("agent", "session.start", self.metadata)

        if install_hooks:
            self._install_hooks()

    def stop(self) -> str:
        """Stop recording and return session ID."""
        if not self.recording:
            logger.warning("No active recording to stop")
            return self.session_id

        self.recording = False
        self.end_time = time.time()
        self.metadata["end_time"] = datetime.now().isoformat()
        self.metadata["duration_seconds"] = self.end_time - self.start_time
        self.metadata["total_events"] = self.event_buffer.count
        self.metadata["total_snapshots"] = len(self.snapshots)

        # Record stop event
        self.event_buffer.record(
            "agent",
            "session.stop",
            {
                "duration": self.metadata["duration_seconds"],
                "events": self.event_buffer.count,
            },
        )

        self._uninstall_hooks()

        logger.info(f"🎬 Session recording stopped: {self.session_id}")
        print(
            f"🎬 Recording stopped: {self.event_buffer.count} events, {len(self.snapshots)} snapshots"
        )

        return self.session_id

    def snapshot(
        self,
        agent=None,
        description: str = "",
        last_query: str = "",
        last_result: str = "",
    ):
        """Create a state snapshot with full conversation state for resume capability.

        Args:
            agent: The agent instance to capture state from
            description: Human-readable description of this snapshot
            last_query: The last user query (for resume context)
            last_result: The last agent result (for resume context)
        """
        if not self.recording:
            return

        self._snapshot_counter += 1

        # Get agent info if available
        messages_count = 0
        tools_loaded = []
        system_prompt_hash = ""
        agent_messages = []
        system_prompt = ""
        model_info = {}

        if agent:
            try:
                # Capture message count
                if hasattr(agent, "messages"):
                    messages_count = len(agent.messages) if agent.messages else 0
                    # NEW: Capture actual messages for resume capability
                    if agent.messages:
                        agent_messages = self._serialize_messages(agent.messages)

                # Capture tools
                if hasattr(agent, "tool_names"):
                    tools_loaded = list(agent.tool_names)

                # Capture system prompt
                if hasattr(agent, "system_prompt"):
                    system_prompt_hash = str(hash(agent.system_prompt))[:16]
                    system_prompt = agent.system_prompt or ""

                # Capture model info safely
                if hasattr(agent, "model"):
                    model = agent.model
                    model_info = {
                        "type": type(model).__name__,
                        "model_id": getattr(model, "model_id", "unknown"),
                        "provider": getattr(model, "provider", "unknown"),
                    }

            except Exception as e:
                logger.debug(f"Could not extract agent state: {e}")

        snapshot = SessionSnapshot(
            timestamp=time.time(),
            snapshot_id=self._snapshot_counter,
            agent_messages_count=messages_count,
            tools_loaded=tools_loaded,
            system_prompt_hash=system_prompt_hash,
            env_vars_redacted=self._redact_env_vars(),
            cwd=os.getcwd(),
            events_since_last=self.event_buffer.count,
            # NEW: Full state for resume
            agent_messages=agent_messages,
            system_prompt=system_prompt,
            last_query=last_query,
            last_result=last_result,
            model_info=model_info,
        )

        self.snapshots.append(snapshot)

        # Record snapshot event
        self.event_buffer.record(
            "agent",
            "snapshot.created",
            {
                "snapshot_id": self._snapshot_counter,
                "description": description,
                "messages_captured": len(agent_messages),
                "has_system_prompt": bool(system_prompt),
            },
        )

        logger.debug(
            f"🎬 Snapshot #{self._snapshot_counter} created with {len(agent_messages)} messages"
        )

    def _serialize_messages(self, messages) -> List[Dict[str, Any]]:
        """Safely serialize agent messages for storage."""
        serialized = []
        for msg in messages:
            try:
                if isinstance(msg, dict):
                    # Already a dict, just copy
                    serialized.append(dict(msg))
                elif hasattr(msg, "__dict__"):
                    # Object with __dict__, convert
                    serialized.append(dict(msg.__dict__))
                elif hasattr(msg, "model_dump"):
                    # Pydantic model
                    serialized.append(msg.model_dump())
                else:
                    # Fallback: convert to string representation
                    serialized.append({"content": str(msg), "role": "unknown"})
            except Exception as e:
                logger.debug(f"Could not serialize message: {e}")
                serialized.append(
                    {"content": str(msg)[:1000], "role": "unknown", "_error": str(e)}
                )
        return serialized

    def record_tool_call(
        self, tool_name: str, args: Dict[str, Any], trace_id: str = None
    ):
        """Record a tool call event."""
        if not self.recording:
            return
        self.event_buffer.record(
            "tool",
            "tool.call",
            {"name": tool_name, "args": self._truncate_data(args)},
            trace_id,
        )

    def record_tool_result(
        self, tool_name: str, result: Any, duration_ms: float = 0, trace_id: str = None
    ):
        """Record a tool result event."""
        if not self.recording:
            return
        self.event_buffer.record(
            "tool",
            "tool.result",
            {
                "name": tool_name,
                "result_preview": str(result)[:500],
                "duration_ms": duration_ms,
            },
            trace_id,
        )

    def record_agent_message(self, role: str, content: str, trace_id: str = None):
        """Record an agent message event."""
        if not self.recording:
            return
        self.event_buffer.record(
            "agent",
            "message",
            {"role": role, "content_preview": content[:500] if content else ""},
            trace_id,
        )

    def record_sys_event(self, event_type: str, data: Dict[str, Any]):
        """Record a system-level event."""
        if not self.recording:
            return
        self.event_buffer.record("sys", event_type, self._truncate_data(data))

    def export(self, output_path: str = None) -> str:
        """Export the session to a ZIP file."""
        if output_path is None:
            output_path = str(RECORDING_DIR / f"{self.session_id}.zip")

        logger.info(f"🎬 Exporting session to {output_path}")

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write events as JSONL
            events_data = "\n".join(
                json.dumps(e.to_dict()) for e in self.event_buffer.get_all()
            )
            zf.writestr("events.jsonl", events_data)

            # Write snapshots as JSON
            snapshots_data = json.dumps([s.to_dict() for s in self.snapshots], indent=2)
            zf.writestr("snapshots.json", snapshots_data)

            # Write metadata
            self.metadata["export_time"] = datetime.now().isoformat()
            zf.writestr("metadata.json", json.dumps(self.metadata, indent=2))

            # Try to serialize snapshots with dill/pickle (for potential state replay)
            try:
                pkl_data = serializer.dumps(
                    {"snapshots": self.snapshots, "metadata": self.metadata}
                )
                zf.writestr("session.pkl", pkl_data)
            except Exception as e:
                logger.warning(f"Could not serialize session state: {e}")
                zf.writestr("session.pkl.error", str(e))

        logger.info(f"🎬 Session exported: {output_path}")
        print(f"🎬 Session exported: {output_path}")
        return output_path

    def _redact_env_vars(self) -> Dict[str, str]:
        """Get environment variables with sensitive values redacted."""
        redacted = {}
        for key, value in os.environ.items():
            if any(pattern in key.upper() for pattern in self.REDACT_PATTERNS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value[:100] if len(value) > 100 else value
        return redacted

    def _truncate_data(self, data: Any, max_len: int = 1000) -> Any:
        """Truncate data to prevent huge events."""
        if isinstance(data, str):
            return data[:max_len] if len(data) > max_len else data
        elif isinstance(data, dict):
            return {
                k: self._truncate_data(v, max_len // 2)
                for k, v in list(data.items())[:20]
            }
        elif isinstance(data, list):
            return [self._truncate_data(v, max_len // 2) for v in data[:10]]
        else:
            return str(data)[:max_len]

    def _install_hooks(self):
        """Install hooks to capture OS-level events."""
        if self._hooks_installed:
            return

        # Hook: builtins.open
        self._original_open = builtins.open
        recorder = self

        def traced_open(file, mode="r", *args, **kwargs):
            if recorder.recording:
                recorder.record_sys_event(
                    "file.open", {"path": str(file), "mode": mode}
                )
            return recorder._original_open(file, mode, *args, **kwargs)

        builtins.open = traced_open

        # Hook: requests (if available)
        try:
            import requests

            self._original_requests_get = requests.get

            def traced_get(url, *args, **kwargs):
                if recorder.recording:
                    recorder.record_sys_event("http.get", {"url": str(url)[:200]})
                return recorder._original_requests_get(url, *args, **kwargs)

            requests.get = traced_get
        except ImportError:
            pass

        self._hooks_installed = True
        logger.info("🎬 Recording hooks installed")

    def _uninstall_hooks(self):
        """Uninstall recording hooks."""
        if not self._hooks_installed:
            return

        if self._original_open:
            builtins.open = self._original_open

        if self._original_requests_get:
            try:
                import requests

                requests.get = self._original_requests_get
            except ImportError:
                pass

        self._hooks_installed = False
        logger.info("🎬 Recording hooks uninstalled")
