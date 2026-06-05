"""AETHON UI — Dashboard and real-time event infrastructure."""

from aethon.ui.event_bus import DashboardEventBus
from aethon.ui.dashboard import setup_dashboard

__all__ = ["DashboardEventBus", "setup_dashboard"]
