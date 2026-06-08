"""Ambient mode tools — runtime on/off switch for the background loop."""

import json

from strands import tool


def create_ambient_tools(manager):
    """Build the ambient-control tools bound to an AmbientModeManager."""

    @tool
    def start_ambient_mode(autonomous: bool = False) -> str:
        """Start ambient (proactive) background mode.

        Ambient mode lets AETHON do useful work during idle time. With
        autonomous=True it works continuously (with a cooldown) until it emits a
        completion signal or hits its iteration cap.

        Args:
            autonomous: Run continuously rather than only when idle.
        """
        return manager.request_start(autonomous)

    @tool
    def stop_ambient_mode() -> str:
        """Stop ambient/autonomous background mode."""
        return manager.request_stop()

    @tool
    def get_ambient_status() -> str:
        """Report ambient mode status (running, autonomous, iterations, pending)."""
        return json.dumps(manager.status())

    return [start_ambient_mode, stop_ambient_mode, get_ambient_status]
