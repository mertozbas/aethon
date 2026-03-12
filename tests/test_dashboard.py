"""Tests for web dashboard endpoints."""

import pytest
from unittest.mock import MagicMock, PropertyMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aethon.ui.dashboard import setup_dashboard


@pytest.fixture
def mock_runtime():
    runtime = MagicMock()
    runtime.agents = {
        "webchat:local": MagicMock(name="AETHON"),
        "telegram:123": MagicMock(name="AETHON"),
    }
    # Set agent name attribute
    for agent in runtime.agents.values():
        agent.name = "AETHON"
    runtime.memory = None
    runtime._telemetry_hook = None
    return runtime


@pytest.fixture
def mock_runtime_with_memory(mock_runtime):
    memory = MagicMock()
    memory.count.return_value = 42
    memory.list_all.return_value = [
        {"content": "Python tercih et", "category": "tercih"},
    ]
    memory.search.return_value = [
        {"content": "Python tercih et", "score": 0.95},
    ]
    mock_runtime.memory = memory
    return mock_runtime


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.model_dump.return_value = {
        "model": {"provider": "ollama", "model_id": "qwen2.5"},
    }
    return config


@pytest.fixture
def app(mock_runtime, mock_config):
    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config)
    return app


@pytest.fixture
def app_with_memory(mock_runtime_with_memory, mock_config):
    app = FastAPI()
    setup_dashboard(app, mock_runtime_with_memory, mock_config)
    return app


def test_dashboard_html(app):
    """GET /dashboard returns HTML page."""
    client = TestClient(app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "AETHON Dashboard" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_api_sessions(app):
    """GET /api/sessions returns session list."""
    client = TestClient(app)
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert len(data["sessions"]) == 2
    ids = [s["session_id"] for s in data["sessions"]]
    assert "webchat:local" in ids
    assert "telegram:123" in ids


def test_api_memory_disabled(app):
    """GET /api/memory returns disabled when no memory."""
    client = TestClient(app)
    resp = client.get("/api/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False


def test_api_memory_enabled(app_with_memory):
    """GET /api/memory returns entries when memory active."""
    client = TestClient(app_with_memory)
    resp = client.get("/api/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["count"] == 42
    assert len(data["entries"]) == 1


def test_api_memory_search(app_with_memory):
    """POST /api/memory/search returns results."""
    client = TestClient(app_with_memory)
    resp = client.post("/api/memory/search", json={"query": "Python"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1


def test_api_memory_search_empty_query(app_with_memory):
    """POST /api/memory/search with empty query returns empty."""
    client = TestClient(app_with_memory)
    resp = client.post("/api/memory/search", json={"query": ""})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_api_config(app, mock_config):
    """GET /api/config returns config dump."""
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "model" in data


def test_api_scheduler_jobs_empty(app):
    """GET /api/scheduler/jobs returns empty when no scheduler."""
    client = TestClient(app)
    resp = client.get("/api/scheduler/jobs")
    assert resp.status_code == 200
    assert resp.json()["jobs"] == []


def test_api_telemetry_disabled(app):
    """GET /api/telemetry returns disabled when no hook."""
    client = TestClient(app)
    resp = client.get("/api/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False


def test_api_telemetry_enabled(mock_runtime, mock_config):
    """GET /api/telemetry returns data when hook active."""
    telemetry = MagicMock()
    telemetry.get_summary.return_value = {
        "total_tool_calls": 10,
        "total_model_calls": 5,
    }
    telemetry.get_metrics.return_value = [
        {"type": "tool", "name": "shell", "duration": 1.5},
    ]
    mock_runtime._telemetry_hook = telemetry

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config)
    client = TestClient(app)
    resp = client.get("/api/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["summary"]["total_tool_calls"] == 10
    assert len(data["metrics"]) == 1
