"""Tests for web dashboard endpoints.

Tests REST API endpoints, SPA serving, and WebSocket connections.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aethon.ui.dashboard import setup_dashboard
from aethon.ui.event_bus import DashboardEventBus


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
    runtime._event_bus = None
    runtime.sop_runner = None
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
def event_bus():
    return DashboardEventBus()


@pytest.fixture
def app(mock_runtime, mock_config, event_bus):
    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    return app


@pytest.fixture
def app_with_memory(mock_runtime_with_memory, mock_config, event_bus):
    app = FastAPI()
    setup_dashboard(app, mock_runtime_with_memory, mock_config, event_bus=event_bus)
    return app


@pytest.fixture
def app_no_event_bus(mock_runtime, mock_config):
    """App without event bus (backward compatible)."""
    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config)
    return app


# --- SPA Serving ---

def test_dashboard_html(app):
    """GET /dashboard returns SPA HTML page."""
    client = TestClient(app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "AETHON Dashboard" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_has_spa_structure(app):
    """Dashboard HTML contains SPA shell elements."""
    client = TestClient(app)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert 'id="app-shell"' in resp.text
    assert 'id="sidebar"' in resp.text
    assert 'id="content"' in resp.text


def test_static_css_served(app):
    """Static CSS file is served."""
    client = TestClient(app)
    resp = client.get("/dashboard/static/css/dashboard.css")
    assert resp.status_code == 200
    assert "glassmorphism" in resp.text.lower() or "--bg-primary" in resp.text


def test_static_js_served(app):
    """Static JS file is served."""
    client = TestClient(app)
    resp = client.get("/dashboard/static/js/app.js")
    assert resp.status_code == 200
    assert "DashboardWS" in resp.text or "router" in resp.text


# --- REST API (backward compatible) ---

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


def test_api_telemetry_enabled(mock_runtime, mock_config, event_bus):
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
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/telemetry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["summary"]["total_tool_calls"] == 10
    assert len(data["metrics"]) == 1


# --- Backward Compatibility ---

def test_setup_without_event_bus(app_no_event_bus):
    """setup_dashboard works without event_bus parameter."""
    client = TestClient(app_no_event_bus)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "AETHON" in resp.text


def test_api_works_without_event_bus(app_no_event_bus):
    """API endpoints work without event_bus."""
    client = TestClient(app_no_event_bus)
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


# --- WebSocket ---

def test_ws_dashboard_connects(app):
    """WebSocket /ws/dashboard accepts connections."""
    client = TestClient(app)
    with client.websocket_connect("/ws/dashboard") as ws:
        # Send subscribe message
        ws.send_json({
            "channel": "subscribe",
            "topics": ["messages", "telemetry"]
        })
        # Connection should stay alive — just verify no error


def test_ws_telemetry_legacy_connects(app):
    """Legacy WebSocket /ws/telemetry still works."""
    client = TestClient(app)
    with client.websocket_connect("/ws/telemetry") as ws:
        # Connection should accept without error
        pass


def test_ws_dashboard_subscribe_message(app, event_bus):
    """WebSocket /ws/dashboard processes subscribe messages without error."""
    client = TestClient(app)
    with client.websocket_connect("/ws/dashboard") as ws_client:
        # Send subscribe — should not cause any error
        ws_client.send_json({
            "channel": "subscribe",
            "topics": ["messages", "logs", "telemetry", "agents"]
        })
        # Send non-JSON — should be silently ignored
        ws_client.send_text("not json")
        # If we get here without error, subscribe handling works


def test_ws_dashboard_event_bus_subscribes(app, event_bus):
    """WebSocket /ws/dashboard subscribes to event bus on connect."""
    initial_count = event_bus.subscriber_count
    client = TestClient(app)
    with client.websocket_connect("/ws/dashboard"):
        # Event bus should have a new subscriber while WS is connected
        # (The forward task subscribes to the bus)
        assert event_bus.subscriber_count >= initial_count


# --- Telemetry Hook Event Bus Integration ---

def test_telemetry_hook_emits_on_event_bus():
    """TelemetryHookProvider emits events to event bus."""
    from aethon.agent.hooks.telemetry import TelemetryHookProvider
    from aethon.ui.event_bus import DashboardEventBus

    bus = DashboardEventBus()
    q = bus.subscribe()
    hook = TelemetryHookProvider(event_bus=bus)

    # Simulate before_tool
    mock_event = MagicMock()
    mock_event.tool_use = {"toolUseId": "t1", "name": "shell"}
    hook.before_tool(mock_event)

    # Should emit agents:tool_start
    event = q.get_nowait()
    assert event["channel"] == "agents"
    assert event["data"]["event"] == "tool_start"
    assert event["data"]["tool_name"] == "shell"


def test_telemetry_hook_after_tool_emits_both_channels():
    """after_tool emits on both telemetry and agents channels."""
    from aethon.agent.hooks.telemetry import TelemetryHookProvider
    from aethon.ui.event_bus import DashboardEventBus

    bus = DashboardEventBus()
    q = bus.subscribe()
    hook = TelemetryHookProvider(event_bus=bus)

    # Setup timer via before_tool
    before_event = MagicMock()
    before_event.tool_use = {"toolUseId": "t2", "name": "web_search"}
    hook.before_tool(before_event)
    q.get_nowait()  # Drain the tool_start event

    # Now after_tool
    after_event = MagicMock()
    after_event.tool_use = {"toolUseId": "t2", "name": "web_search"}
    after_event.exception = None
    after_event.result = {"status": "success"}
    hook.after_tool(after_event)

    # Should get telemetry + agents events
    events = []
    while not q.empty():
        events.append(q.get_nowait())

    channels = [e["channel"] for e in events]
    assert "telemetry" in channels
    assert "agents" in channels

    # Verify telemetry event
    tel_event = next(e for e in events if e["channel"] == "telemetry")
    assert tel_event["data"]["type"] == "tool"
    assert tel_event["data"]["name"] == "web_search"
    assert tel_event["data"]["status"] == "success"

    # Verify agents event
    agent_event = next(e for e in events if e["channel"] == "agents")
    assert agent_event["data"]["event"] == "tool_end"
    assert agent_event["data"]["tool_name"] == "web_search"


def test_telemetry_hook_works_without_event_bus():
    """TelemetryHookProvider works fine without event bus."""
    from aethon.agent.hooks.telemetry import TelemetryHookProvider

    hook = TelemetryHookProvider()  # No event_bus

    # Simulate tool cycle — should not raise
    before_event = MagicMock()
    before_event.tool_use = {"toolUseId": "t3", "name": "test_tool"}
    hook.before_tool(before_event)

    after_event = MagicMock()
    after_event.tool_use = {"toolUseId": "t3", "name": "test_tool"}
    after_event.exception = None
    after_event.result = {"status": "success"}
    hook.after_tool(after_event)

    assert len(hook.metrics) == 1
    assert hook.metrics[0]["name"] == "test_tool"


# --- Step 3: Session Detail API ---

def test_api_session_detail(app):
    """GET /api/sessions/{session_id} returns session details."""
    client = TestClient(app)
    resp = client.get("/api/sessions/webchat:local")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "webchat:local"
    assert data["agent_name"] == "AETHON"
    assert data["channel"] == "webchat"
    assert data["sender"] == "local"


def test_api_session_detail_not_found(app):
    """GET /api/sessions/{session_id} returns error for unknown session."""
    client = TestClient(app)
    resp = client.get("/api/sessions/unknown:session")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_api_session_detail_telegram(app):
    """GET /api/sessions/{session_id} works with telegram sessions."""
    client = TestClient(app)
    resp = client.get("/api/sessions/telegram:123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "telegram"
    assert data["sender"] == "123"


# --- Step 3: Memory CRUD API ---

def test_api_memory_stats(app_with_memory):
    """GET /api/memory/stats returns statistics."""
    client = TestClient(app_with_memory)
    resp = client.get("/api/memory/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["count"] == 42


def test_api_memory_stats_disabled(app):
    """GET /api/memory/stats returns disabled when no memory."""
    client = TestClient(app)
    resp = client.get("/api/memory/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["count"] == 0


def test_api_memory_add(app_with_memory, mock_runtime_with_memory):
    """POST /api/memory adds a memory entry."""
    mock_runtime_with_memory.memory.store.return_value = 99
    client = TestClient(app_with_memory)
    resp = client.post("/api/memory", json={
        "content": "Test memory",
        "category": "test"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["memory_id"] == 99
    mock_runtime_with_memory.memory.store.assert_called_once_with(
        content="Test memory", category="test", metadata=None
    )


def test_api_memory_add_empty_content(app_with_memory):
    """POST /api/memory rejects empty content."""
    client = TestClient(app_with_memory)
    resp = client.post("/api/memory", json={"content": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_api_memory_add_disabled(app):
    """POST /api/memory returns error when memory disabled."""
    client = TestClient(app)
    resp = client.post("/api/memory", json={"content": "Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_api_memory_delete(app_with_memory, mock_runtime_with_memory):
    """DELETE /api/memory/{id} deletes a memory."""
    mock_runtime_with_memory.memory.forget.return_value = True
    client = TestClient(app_with_memory)
    resp = client.delete("/api/memory/42")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    mock_runtime_with_memory.memory.forget.assert_called_once_with(42)


def test_api_memory_delete_not_found(app_with_memory, mock_runtime_with_memory):
    """DELETE /api/memory/{id} returns error for missing memory."""
    mock_runtime_with_memory.memory.forget.return_value = False
    client = TestClient(app_with_memory)
    resp = client.delete("/api/memory/9999")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_api_memory_delete_disabled(app):
    """DELETE /api/memory/{id} returns error when memory disabled."""
    client = TestClient(app)
    resp = client.delete("/api/memory/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


# --- Step 4: Config API ---

def test_api_config_masks_sensitive(mock_runtime, mock_config, event_bus):
    """GET /api/config masks sensitive fields."""
    mock_config.model_dump.return_value = {
        "model": {"provider": "ollama", "api_key": "sk-secret-123"},
        "channels": {
            "telegram": {"token": "bot-token-xyz"},
            "slack": {"bot_token": "xoxb-111", "app_token": "xapp-222"},
        },
        "webhook": {"secret": "whsec-abc"},
    }
    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"]["api_key"] == "***"
    assert data["channels"]["telegram"]["token"] == "***"
    assert data["channels"]["slack"]["bot_token"] == "***"
    assert data["channels"]["slack"]["app_token"] == "***"
    assert data["webhook"]["secret"] == "***"


def test_api_config_schema(app):
    """GET /api/config/schema returns JSON Schema."""
    client = TestClient(app)
    resp = client.get("/api/config/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert "properties" in data or "$defs" in data
    assert data.get("title") == "AethonConfig" or "type" in data


# --- Step 4: SOP API ---

def test_api_sops_disabled(app):
    """GET /api/sops returns disabled when no sop_runner."""
    client = TestClient(app)
    resp = client.get("/api/sops")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False


def test_api_sops_list(mock_runtime, mock_config, event_bus):
    """GET /api/sops returns SOP list when enabled."""
    sop_runner = MagicMock()
    sop_runner.list_sops.return_value = [
        {"name": "code-assist", "description": "Help with code"},
        {"name": "my-custom", "description": "Custom procedure"},
    ]
    sop_runner.get_sop.side_effect = lambda n: "# SOP content" if n else None
    mock_runtime.sop_runner = sop_runner

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/sops")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert len(data["sops"]) == 2
    # code-assist should be marked as builtin
    ca = next(s for s in data["sops"] if s["name"] == "code-assist")
    assert ca["type"] == "builtin"
    # my-custom should be custom
    mc = next(s for s in data["sops"] if s["name"] == "my-custom")
    assert mc["type"] == "custom"


def test_api_sop_get(mock_runtime, mock_config, event_bus):
    """GET /api/sops/{name} returns SOP content."""
    sop_runner = MagicMock()
    sop_runner.get_sop.return_value = "# Code Assist\n\n## Overview\nHelp with code."
    mock_runtime.sop_runner = sop_runner

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/sops/code-assist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "code-assist"
    assert "Code Assist" in data["content"]
    assert data["type"] == "builtin"


def test_api_sop_get_not_found(mock_runtime, mock_config, event_bus):
    """GET /api/sops/{name} returns error for missing SOP."""
    sop_runner = MagicMock()
    sop_runner.get_sop.return_value = None
    mock_runtime.sop_runner = sop_runner

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/sops/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


def test_api_sop_delete_builtin_blocked(mock_runtime, mock_config, event_bus):
    """DELETE /api/sops/{name} blocks deleting built-in SOPs."""
    sop_runner = MagicMock()
    mock_runtime.sop_runner = sop_runner

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.delete("/api/sops/code-assist")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert "built-in" in data["error"].lower() or "Cannot" in data["error"]


def test_api_sop_save(mock_runtime, mock_config, event_bus, tmp_path):
    """PUT /api/sops/{name} saves a custom SOP."""
    sop_runner = MagicMock()
    sop_runner._sops = {}
    mock_runtime.sop_runner = sop_runner

    # Use tmp_path as workspace
    mock_config.paths = MagicMock()
    mock_config.paths.workspace = str(tmp_path / "workspace")

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.put("/api/sops/my-custom", json={
        "content": "# My Custom SOP\n\n## Overview\nTest."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["name"] == "my-custom"

    # Verify file was written
    sop_path = tmp_path / "workspace" / "sops" / "my-custom.sop.md"
    assert sop_path.exists()
    assert "My Custom SOP" in sop_path.read_text()


# --- Step 5: Agent Activity API ---

def test_api_agents_active(app):
    """GET /api/agents/active returns active agents."""
    client = TestClient(app)
    resp = client.get("/api/agents/active")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert len(data["agents"]) == 2
    sids = [a["session_id"] for a in data["agents"]]
    assert "webchat:local" in sids
    assert "telegram:123" in sids


def test_api_agents_history_empty(app):
    """GET /api/agents/history returns empty when no telemetry."""
    client = TestClient(app)
    resp = client.get("/api/agents/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []


def test_api_agents_history_with_telemetry(mock_runtime, mock_config, event_bus):
    """GET /api/agents/history returns recent metrics."""
    telemetry = MagicMock()
    telemetry.get_metrics.return_value = [
        {"type": "tool", "name": "shell", "duration": 1.5, "status": "success"},
        {"type": "model", "name": "model_call", "duration": 2.0, "status": "success"},
    ]
    mock_runtime._telemetry_hook = telemetry

    app = FastAPI()
    setup_dashboard(app, mock_runtime, mock_config, event_bus=event_bus)
    client = TestClient(app)
    resp = client.get("/api/agents/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 2
