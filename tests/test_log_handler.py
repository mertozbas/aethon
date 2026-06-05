"""Tests for WebSocketLogHandler and log forwarding."""

import logging
import pytest

from aethon.ui.event_bus import DashboardEventBus
from aethon.ui.log_handler import WebSocketLogHandler, setup_log_forwarding


@pytest.fixture
def event_bus():
    return DashboardEventBus()


def test_handler_emits_log_record(event_bus):
    """WebSocketLogHandler emits log records to the event bus."""
    q = event_bus.subscribe()
    handler = WebSocketLogHandler(event_bus, level=logging.DEBUG)

    logger = logging.getLogger("test.handler_emit")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.info("Test log message")

        assert not q.empty()
        event = q.get_nowait()
        assert event["channel"] == "logs"
        assert event["data"]["level"] == "INFO"
        assert event["data"]["message"] == "Test log message"
        assert event["data"]["module"] == "handler_emit"
        assert event["data"]["logger"] == "test.handler_emit"
        assert "timestamp" in event["data"]
    finally:
        logger.removeHandler(handler)


def test_handler_respects_level(event_bus):
    """Handler only forwards records at or above its configured level."""
    q = event_bus.subscribe()
    handler = WebSocketLogHandler(event_bus, level=logging.WARNING)

    logger = logging.getLogger("test.level_filter")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.debug("This should be filtered")
        logger.info("This too should be filtered")
        logger.warning("This should pass")

        # Only the WARNING should be emitted
        assert not q.empty()
        event = q.get_nowait()
        assert event["data"]["level"] == "WARNING"
        assert event["data"]["message"] == "This should pass"
        assert q.empty()
    finally:
        logger.removeHandler(handler)


def test_handler_captures_all_levels(event_bus):
    """Handler captures DEBUG, INFO, WARNING, ERROR, CRITICAL levels."""
    q = event_bus.subscribe()
    handler = WebSocketLogHandler(event_bus, level=logging.DEBUG)

    logger = logging.getLogger("test.all_levels")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")
        logger.critical("critical msg")

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        levels = [e["data"]["level"] for e in events]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    finally:
        logger.removeHandler(handler)


def test_handler_module_extraction(event_bus):
    """Handler extracts the last segment of logger name as module."""
    q = event_bus.subscribe()
    handler = WebSocketLogHandler(event_bus, level=logging.DEBUG)

    logger = logging.getLogger("aethon.gateway.router")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.info("router test")

        event = q.get_nowait()
        assert event["data"]["module"] == "router"
        assert event["data"]["logger"] == "aethon.gateway.router"
    finally:
        logger.removeHandler(handler)


def test_handler_root_logger_module(event_bus):
    """Handler handles root logger name gracefully."""
    q = event_bus.subscribe()
    handler = WebSocketLogHandler(event_bus, level=logging.DEBUG)

    logger = logging.getLogger("root_test")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        logger.info("root test")

        event = q.get_nowait()
        # Single segment name — module is the name itself
        assert event["data"]["module"] == "root_test"
    finally:
        logger.removeHandler(handler)


def test_setup_log_forwarding_returns_handler(event_bus):
    """setup_log_forwarding returns a handler and attaches to aethon logger."""
    handler = setup_log_forwarding(event_bus, level=logging.INFO)

    assert isinstance(handler, WebSocketLogHandler)

    # Verify it's attached to the aethon logger
    aethon_logger = logging.getLogger("aethon")
    assert handler in aethon_logger.handlers

    # Clean up
    aethon_logger.removeHandler(handler)


def test_setup_log_forwarding_captures_aethon_logs(event_bus):
    """setup_log_forwarding makes aethon.* logs flow to event bus."""
    q = event_bus.subscribe()
    handler = setup_log_forwarding(event_bus, level=logging.DEBUG)

    # Use a child logger of aethon
    logger = logging.getLogger("aethon.test.forwarding")
    logger.setLevel(logging.DEBUG)

    try:
        logger.info("Forwarded log")

        assert not q.empty()
        event = q.get_nowait()
        assert event["channel"] == "logs"
        assert event["data"]["message"] == "Forwarded log"
        assert event["data"]["logger"] == "aethon.test.forwarding"
    finally:
        aethon_logger = logging.getLogger("aethon")
        aethon_logger.removeHandler(handler)


def test_handler_survives_event_bus_error(event_bus):
    """Handler does not crash if event bus raises during emit."""
    handler = WebSocketLogHandler(event_bus, level=logging.DEBUG)

    # Replace emit with something that raises
    original_emit = event_bus.emit
    event_bus.emit = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bus error"))

    logger = logging.getLogger("test.error_resilience")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        # Should not raise
        logger.info("This should not crash")
    finally:
        logger.removeHandler(handler)
        event_bus.emit = original_emit
