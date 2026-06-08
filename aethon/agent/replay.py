"""Session replay — load a recorded session ZIP for analysis and resume.

Vendored ``LoadedSession``: reads events.jsonl / snapshots.json / metadata.json /
session.pkl from a recording ZIP and exposes filtering + snapshot-resume helpers.
"""

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aethon.agent.session_recording import (
    RecordedEvent,
    SessionSnapshot,
    logger,
    serializer,
)

class LoadedSession:
    """A loaded session from a ZIP file for replay and analysis.

    Provides access to recorded events, snapshots, and metadata.
    Can be used to resume agent state from a specific snapshot.

    Example:
        session = load_session("session-20260202-224751.zip")
        print(session.metadata)
        print(session.events[:10])

        # Resume from snapshot
        session.resume_from_snapshot(2)
    """

    def __init__(self, zip_path: str):
        """Load a session from a ZIP file."""
        self.zip_path = Path(zip_path)
        self.events: List[RecordedEvent] = []
        self.snapshots: List[SessionSnapshot] = []
        self.metadata: Dict[str, Any] = {}
        self._pkl_data: Optional[Dict] = None

        self._load()

    def _load(self):
        """Load and parse the session ZIP file."""
        if not self.zip_path.exists():
            raise FileNotFoundError(f"Session file not found: {self.zip_path}")

        with zipfile.ZipFile(self.zip_path, "r") as zf:
            # Load events.jsonl
            if "events.jsonl" in zf.namelist():
                events_text = zf.read("events.jsonl").decode("utf-8")
                for line in events_text.strip().split("\n"):
                    if line:
                        data = json.loads(line)
                        self.events.append(RecordedEvent(**data))

            # Load snapshots.json
            if "snapshots.json" in zf.namelist():
                snapshots_text = zf.read("snapshots.json").decode("utf-8")
                snapshots_data = json.loads(snapshots_text)
                for snap_data in snapshots_data:
                    self.snapshots.append(SessionSnapshot(**snap_data))

            # Load metadata.json
            if "metadata.json" in zf.namelist():
                metadata_text = zf.read("metadata.json").decode("utf-8")
                self.metadata = json.loads(metadata_text)

            # Load session.pkl if available
            if "session.pkl" in zf.namelist():
                try:
                    pkl_data = zf.read("session.pkl")
                    self._pkl_data = serializer.loads(pkl_data)
                except Exception as e:
                    logger.warning(f"Could not load session.pkl: {e}")

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self.metadata.get("session_id", "unknown")

    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        return self.metadata.get("duration_seconds", 0.0)

    @property
    def has_pkl(self) -> bool:
        """Check if session has serialized state for resuming."""
        return self._pkl_data is not None

    def get_events_by_layer(self, layer: str) -> List[RecordedEvent]:
        """Get events filtered by layer (sys, tool, agent)."""
        return [e for e in self.events if e.layer == layer]

    def get_events_by_type(self, event_type: str) -> List[RecordedEvent]:
        """Get events filtered by type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(self, start_ns: int, end_ns: int) -> List[RecordedEvent]:
        """Get events within a timestamp range."""
        return [e for e in self.events if start_ns <= e.timestamp_ns <= end_ns]

    def get_snapshot(self, snapshot_id: int) -> Optional[SessionSnapshot]:
        """Get a specific snapshot by ID."""
        for snap in self.snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None

    def get_events_until_snapshot(self, snapshot_id: int) -> List[RecordedEvent]:
        """Get all events up to a specific snapshot."""
        snap = self.get_snapshot(snapshot_id)
        if not snap:
            return []

        snap_time_ns = int(snap.timestamp * 1e9)
        return [e for e in self.events if e.timestamp_ns <= snap_time_ns]

    def resume_from_snapshot(
        self, snapshot_id: int, agent: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Resume agent state from a specific snapshot.

        This reconstructs the agent context based on the snapshot state.
        If an agent is provided, it will be configured with the snapshot state
        including restored conversation history.

        Args:
            snapshot_id: The snapshot ID to resume from
            agent: Optional agent instance to configure

        Returns:
            Dict with resume status, snapshot info, and continuation prompt
        """
        snap = self.get_snapshot(snapshot_id)
        if not snap:
            return {"status": "error", "message": f"Snapshot #{snapshot_id} not found"}

        result = {
            "status": "success",
            "snapshot_id": snapshot_id,
            "timestamp": datetime.fromtimestamp(snap.timestamp).isoformat(),
            "cwd": snap.cwd,
            "tools_loaded": snap.tools_loaded,
            "messages_count": snap.agent_messages_count,
            "events_before_snapshot": len(self.get_events_until_snapshot(snapshot_id)),
            "messages_restored": 0,
            "continuation_prompt": "",
        }

        # Change to snapshot's working directory
        if os.path.exists(snap.cwd):
            os.chdir(snap.cwd)
            result["cwd_changed"] = True
        else:
            result["cwd_changed"] = False
            result["cwd_warning"] = f"Directory not found: {snap.cwd}"

        # If agent provided, restore full state
        if agent is not None:
            try:
                # Restore conversation history (the key enhancement!)
                if snap.agent_messages:
                    agent.messages = snap.agent_messages
                    result["messages_restored"] = len(snap.agent_messages)
                    logger.info(
                        f"Restored {len(snap.agent_messages)} messages to agent"
                    )

                # Check tool compatibility
                if hasattr(agent, "tool_registry"):
                    current_tools = set(agent.tool_registry.registry.keys())
                    snapshot_tools = set(snap.tools_loaded)

                    result["tools_match"] = current_tools == snapshot_tools
                    result["missing_tools"] = list(snapshot_tools - current_tools)
                    result["extra_tools"] = list(current_tools - snapshot_tools)

            except Exception as e:
                result["agent_restore_error"] = str(e)
                logger.error(f"Error restoring agent state: {e}")

        # Build continuation prompt (like research_agent_runner pattern)
        if snap.last_query or snap.last_result:
            result["continuation_prompt"] = self._build_continuation_prompt(snap)

        # Include model info if available
        if snap.model_info:
            result["model_info"] = snap.model_info

        logger.info(
            f"Resumed from snapshot #{snapshot_id}: {result['messages_restored']} messages restored"
        )
        return result

    def _build_continuation_prompt(self, snap: SessionSnapshot) -> str:
        """Build a continuation prompt from snapshot context.

        This follows the pattern from research_agent_runner.py for
        seamless conversation continuation.
        """
        prompt_parts = []

        prompt_parts.append("=== RESUMED SESSION CONTEXT ===")
        prompt_parts.append(f"Session: {self.session_id}")
        prompt_parts.append(
            f"Snapshot: #{snap.snapshot_id} from {datetime.fromtimestamp(snap.timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        prompt_parts.append(f"Working Directory: {snap.cwd}")

        if snap.last_query:
            prompt_parts.append(f"\n--- Previous Query ---\n{snap.last_query}")

        if snap.last_result:
            # Truncate long results
            result_preview = snap.last_result[:2000]
            if len(snap.last_result) > 2000:
                result_preview += "\n... [truncated]"
            prompt_parts.append(f"\n--- Previous Result ---\n{result_preview}")

        prompt_parts.append("\n=== END RESUMED CONTEXT ===")
        prompt_parts.append(
            "\nPlease continue from where we left off. The conversation history has been restored."
        )

        return "\n".join(prompt_parts)

    def resume_and_continue(
        self, snapshot_id: int, new_query: str, agent: Any
    ) -> Dict[str, Any]:
        """Resume from snapshot and immediately continue with a new query.

        This is a convenience method that:
        1. Restores agent state from snapshot
        2. Runs the agent with context-aware continuation prompt

        Args:
            snapshot_id: The snapshot ID to resume from
            new_query: The new query to run after resuming
            agent: The agent instance to use

        Returns:
            Dict with resume status and agent result
        """
        # First, resume the state
        resume_result = self.resume_from_snapshot(snapshot_id, agent)

        if resume_result["status"] != "success":
            return resume_result

        # Build the continuation query
        continuation_prompt = resume_result.get("continuation_prompt", "")
        if continuation_prompt:
            full_query = f"{continuation_prompt}\n\n--- New Query ---\n{new_query}"
        else:
            full_query = new_query

        # Run the agent
        try:
            agent_result = agent(full_query)
            resume_result["agent_result"] = str(agent_result)
            resume_result["continuation_successful"] = True
        except Exception as e:
            resume_result["agent_result"] = None
            resume_result["continuation_error"] = str(e)
            resume_result["continuation_successful"] = False

        return resume_result

    def replay_events(
        self,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
        callback: Optional[Callable[[RecordedEvent, int], None]] = None,
    ) -> List[RecordedEvent]:
        """Replay events with optional callback for each event.

        Args:
            start_idx: Starting event index
            end_idx: Ending event index (exclusive), None for all
            callback: Optional function called for each event (event, index)

        Returns:
            List of replayed events
        """
        end = end_idx if end_idx is not None else len(self.events)
        replayed = []

        for i in range(start_idx, min(end, len(self.events))):
            event = self.events[i]
            replayed.append(event)
            if callback:
                callback(event, i)

        return replayed

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON export."""
        return {
            "metadata": self.metadata,
            "events": [e.to_dict() for e in self.events],
            "snapshots": [s.to_dict() for s in self.snapshots],
            "summary": {
                "total_events": len(self.events),
                "total_snapshots": len(self.snapshots),
                "events_by_layer": {
                    "sys": len(self.get_events_by_layer("sys")),
                    "tool": len(self.get_events_by_layer("tool")),
                    "agent": len(self.get_events_by_layer("agent")),
                },
                "has_resumable_state": self.has_pkl,
            },
        }

    def __repr__(self) -> str:
        return (
            f"LoadedSession(id={self.session_id}, "
            f"events={len(self.events)}, "
            f"snapshots={len(self.snapshots)}, "
            f"duration={self.duration:.1f}s)"
        )

