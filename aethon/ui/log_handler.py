"""WebSocket log handler.

Bridges Python's logging system to the dashboard event bus,
enabling real-time log streaming to the browser.
"""

import logging
from datetime import datetime


class WebSocketLogHandler(logging.Handler):
    """Logging handler that emits log records to the dashboard event bus.

    Records are emitted on the 'logs' channel with level, module, message,
    and timestamp fields.

    Args:
        event_bus: DashboardEventBus instance.
        level: Minimum log level (default: logging.DEBUG).
    """

    def __init__(self, event_bus, level: int = logging.DEBUG):
        super().__init__(level)
        self._event_bus = event_bus

    def emit(self, record: logging.LogRecord) -> None:
        """Format and emit a log record to the event bus."""
        try:
            msg = self.format(record) if self.formatter else record.getMessage()

            self._event_bus.emit("logs", {
                "level": record.levelname,
                "module": record.name.split(".")[-1] if record.name else "root",
                "logger": record.name or "root",
                "message": msg,
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            })
        except Exception:
            self.handleError(record)


def setup_log_forwarding(event_bus, level: int = logging.INFO) -> WebSocketLogHandler:
    """Attach a WebSocketLogHandler to the root 'aethon' logger.

    Args:
        event_bus: DashboardEventBus instance.
        level: Minimum log level to forward.

    Returns:
        The created handler (for later removal if needed).
    """
    handler = WebSocketLogHandler(event_bus, level=level)
    handler.setFormatter(logging.Formatter("%(message)s"))

    # Attach to the aethon root logger
    aethon_logger = logging.getLogger("aethon")
    aethon_logger.addHandler(handler)

    return handler
