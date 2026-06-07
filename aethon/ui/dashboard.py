"""Web dashboard for AETHON monitoring.

Full SPA dashboard with real-time WebSocket support.
Serves static files (HTML/CSS/JS) and provides REST API endpoints
for sessions, memory, telemetry, config, and scheduled jobs.

Phase 5 — Dashboard & UX Revolution.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Request, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


logger = logging.getLogger("aethon.dashboard")

# Path to static files directory (relative to this module)
_STATIC_DIR = Path(__file__).parent / "static"


def setup_dashboard(app, runtime, config, event_bus=None):
    """Register dashboard routes on the FastAPI app.

    Args:
        app: FastAPI application instance.
        runtime: AethonRuntime for data access.
        config: AethonConfig.
        event_bus: Optional DashboardEventBus for real-time events.
    """
    # Attach log forwarding so Python logs stream to dashboard via event bus
    if event_bus:
        try:
            from aethon.ui.log_handler import setup_log_forwarding
            setup_log_forwarding(event_bus, level=logging.DEBUG)
        except Exception as e:
            logger.warning(f"Log forwarding setup failed: {e}")

    # --- Authentication (optional shared token) ---
    # Empty token = no auth (fine for the default localhost bind). When set, all
    # /api/* and /ws/dashboard access requires the token.
    _raw_token = getattr(config.dashboard, "auth_token", "")
    auth_token = _raw_token.strip() if isinstance(_raw_token, str) else ""

    def _provided_token(request: Request) -> str:
        header = request.headers.get("authorization", "")
        bearer = header[7:] if header[:7].lower() == "bearer " else ""
        return request.cookies.get("aethon_dash") or bearer or request.query_params.get("token", "")

    if auth_token:
        _protected = (
            "/api/sessions",
            "/api/memory",
            "/api/config",
            "/api/scheduler",
            "/api/telemetry",
            "/api/sops",
            "/api/agents",
        )

        @app.middleware("http")
        async def _dashboard_auth(request: Request, call_next):
            path = request.url.path
            if path == "/dashboard" or path.startswith(_protected):
                if _provided_token(request) != auth_token:
                    if path == "/dashboard":
                        return HTMLResponse(
                            "<html><body><h3>AETHON dashboard</h3><p>This dashboard is "
                            "protected. Open <code>/dashboard?token=YOUR_TOKEN</code>.</p>"
                            "</body></html>",
                            status_code=401,
                        )
                    return JSONResponse({"detail": "Dashboard authentication required"}, status_code=401)
                response = await call_next(request)
                if path == "/dashboard":
                    response.set_cookie("aethon_dash", auth_token, httponly=True, samesite="strict")
                return response
            return await call_next(request)

    # --- Static file serving ---

    # Mount static files directory for CSS/JS assets
    if _STATIC_DIR.exists():
        app.mount(
            "/dashboard/static",
            StaticFiles(directory=str(_STATIC_DIR)),
            name="dashboard-static",
        )

    @app.get("/dashboard")
    async def dashboard():
        """Serve the SPA index.html."""
        index_path = _STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        # Fallback: minimal HTML
        return HTMLResponse(
            '<html><body><p>Dashboard static files not found.</p></body></html>',
            status_code=500,
        )

    # --- REST API Endpoints (backward compatible) ---

    @app.get("/api/sessions")
    async def api_sessions():
        """List active sessions."""
        sessions = []
        for sid, agent in runtime.agents.items():
            sessions.append({
                "session_id": sid,
                "agent_name": getattr(agent, "name", "AETHON"),
            })
        return {"sessions": sessions, "count": len(sessions)}

    @app.get("/api/memory")
    async def api_memory():
        """Memory statistics and recent entries."""
        if not runtime.memory:
            return {"enabled": False, "count": 0, "entries": []}
        entries = runtime.memory.list_all(limit=20)
        return {
            "enabled": True,
            "count": runtime.memory.count(),
            "entries": entries,
        }

    @app.post("/api/memory/search")
    async def api_memory_search(request_body: dict):
        """Search memory."""
        if not runtime.memory:
            return {"results": []}
        query = request_body.get("query", "")
        if not query:
            return {"results": []}
        results = runtime.memory.search(query, top_k=10)
        return {"results": results}

    # Sensitive field names to mask in config display
    _SENSITIVE_KEYS = {"api_key", "token", "bot_token", "app_token", "secret", "password"}

    def _mask_sensitive(obj):
        """Recursively mask sensitive values in config dicts."""
        if isinstance(obj, dict):
            return {
                k: ("***" if k in _SENSITIVE_KEYS and v else _mask_sensitive(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_mask_sensitive(v) for v in obj]
        return obj

    @app.get("/api/config")
    async def api_config():
        """Current configuration (sensitive fields masked)."""
        return _mask_sensitive(config.model_dump())

    @app.get("/api/config/schema")
    async def api_config_schema():
        """JSON Schema for AethonConfig (for auto-form generation)."""
        from aethon.config import AethonConfig
        return AethonConfig.model_json_schema()

    @app.get("/api/scheduler/jobs")
    async def api_scheduler_jobs():
        """List scheduled jobs."""
        from aethon.tools.scheduler import _scheduler_instance
        if not _scheduler_instance:
            return {"jobs": []}
        return {"jobs": _scheduler_instance.list_jobs()}

    @app.get("/api/telemetry")
    async def api_telemetry():
        """Telemetry summary and recent metrics."""
        telemetry_hook = getattr(runtime, "_telemetry_hook", None)
        if not telemetry_hook:
            return {"enabled": False, "summary": {}, "metrics": []}
        return {
            "enabled": True,
            "summary": telemetry_hook.get_summary(),
            "metrics": telemetry_hook.get_metrics(limit=50),
        }

    # --- Session Detail API (Step 3) ---

    @app.get("/api/sessions/{session_id:path}")
    async def api_session_detail(session_id: str):
        """Get session metadata."""
        agent = runtime.agents.get(session_id)
        if not agent:
            return {"error": "Session not found", "session_id": session_id}

        # Extract channel and sender from session_id
        parts = session_id.split(":", 1)
        channel = parts[0] if parts else "unknown"
        sender = parts[1] if len(parts) > 1 else "unknown"

        return {
            "session_id": session_id,
            "agent_name": getattr(agent, "name", "AETHON"),
            "channel": channel,
            "sender": sender,
        }

    # --- Enhanced Memory API (Step 3) ---

    @app.get("/api/memory/stats")
    async def api_memory_stats():
        """Memory statistics: count, categories, DB size."""
        if not runtime.memory:
            return {"enabled": False, "count": 0, "categories": {}, "db_size_bytes": 0}

        count = runtime.memory.count()

        # Get category breakdown
        try:
            rows = runtime.memory.db.execute(
                "SELECT category, COUNT(*) FROM memories GROUP BY category"
            ).fetchall()
            categories = {r[0]: r[1] for r in rows}
        except Exception:
            categories = {}

        # Get DB file size
        db_size = 0
        try:
            db_path = runtime.memory.db_path
            if db_path.exists():
                db_size = db_path.stat().st_size
        except Exception:
            pass

        return {
            "enabled": True,
            "count": count,
            "categories": categories,
            "db_size_bytes": db_size,
        }

    @app.post("/api/memory")
    async def api_memory_add(request_body: dict):
        """Add a new memory entry."""
        if not runtime.memory:
            return {"error": "Memory is not enabled"}
        content = request_body.get("content", "").strip()
        if not content:
            return {"error": "Content is required"}
        category = request_body.get("category", "general")
        metadata = request_body.get("metadata")

        try:
            memory_id = runtime.memory.store(
                content=content, category=category, metadata=metadata
            )
            return {"success": True, "memory_id": memory_id}
        except Exception as e:
            logger.warning(f"Memory store error: {e}")
            return {"error": str(e)}

    @app.delete("/api/memory/{memory_id}")
    async def api_memory_delete(memory_id: int):
        """Delete a memory entry by ID."""
        if not runtime.memory:
            return {"error": "Memory is not enabled"}

        deleted = runtime.memory.forget(memory_id)
        if deleted:
            return {"success": True, "memory_id": memory_id}
        return {"error": "Memory not found", "memory_id": memory_id}

    # --- SOP API (Step 4) ---

    @app.get("/api/sops")
    async def api_sops():
        """List all available SOPs."""
        if not runtime.sop_runner:
            return {"sops": [], "enabled": False}
        sops = runtime.sop_runner.list_sops()
        # Annotate with type (builtin vs custom)
        for sop in sops:
            content = runtime.sop_runner.get_sop(sop["name"]) or ""
            sop["type"] = "builtin" if sop["name"] in ("code-assist", "pdd", "codebase-summary") else "custom"
            sop["size"] = len(content)
        return {"sops": sops, "enabled": True}

    @app.get("/api/sops/{name}")
    async def api_sop_get(name: str):
        """Get SOP content by name."""
        if not runtime.sop_runner:
            return {"error": "SOPs not enabled"}
        content = runtime.sop_runner.get_sop(name)
        if content is None:
            return {"error": f"SOP '{name}' not found"}
        sop_type = "builtin" if name in ("code-assist", "pdd", "codebase-summary") else "custom"
        return {"name": name, "content": content, "type": sop_type}

    @app.put("/api/sops/{name}")
    async def api_sop_save(name: str, request_body: dict):
        """Save a custom SOP."""
        content = request_body.get("content", "")
        if not content:
            return {"error": "Content is required"}

        # Only save to workspace custom SOPs directory
        sop_dir = Path(config.paths.workspace).expanduser() / "sops"
        sop_dir.mkdir(parents=True, exist_ok=True)
        sop_path = sop_dir / f"{name}.sop.md"

        try:
            sop_path.write_text(content, encoding="utf-8")
            # Reload SOP in runner if available
            if runtime.sop_runner:
                runtime.sop_runner._sops[name] = content
            return {"success": True, "name": name, "path": str(sop_path)}
        except Exception as e:
            logger.warning(f"SOP save error: {e}")
            return {"error": str(e)}

    @app.delete("/api/sops/{name}")
    async def api_sop_delete(name: str):
        """Delete a custom SOP (built-in SOPs cannot be deleted)."""
        if name in ("code-assist", "pdd", "codebase-summary"):
            return {"error": "Cannot delete built-in SOPs"}

        sop_dir = Path(config.paths.workspace).expanduser() / "sops"
        sop_path = sop_dir / f"{name}.sop.md"

        if sop_path.exists():
            try:
                sop_path.unlink()
                if runtime.sop_runner and name in runtime.sop_runner._sops:
                    del runtime.sop_runner._sops[name]
                return {"success": True, "name": name}
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"SOP '{name}' not found on disk"}

    # --- Agent Activity API (Step 5) ---

    @app.get("/api/agents/active")
    async def api_agents_active():
        """List active agents with their status."""
        agents = []
        for sid, agent in runtime.agents.items():
            agents.append({
                "session_id": sid,
                "agent_name": getattr(agent, "name", "AETHON"),
                "agent_id": getattr(agent, "agent_id", "main"),
            })
        # Include specialist agents if available
        factory = getattr(runtime, "specialist_factory", None)
        if factory:
            cache = getattr(factory, "_cache", {})
            for role, agent in cache.items():
                agents.append({
                    "session_id": f"specialist:{role}",
                    "agent_name": getattr(agent, "name", role),
                    "agent_id": role,
                })
        return {"agents": agents, "count": len(agents)}

    @app.get("/api/agents/history")
    async def api_agents_history():
        """Recent agent activity from telemetry metrics."""
        telemetry_hook = getattr(runtime, "_telemetry_hook", None)
        if not telemetry_hook:
            return {"events": []}
        # Return recent tool + model calls as activity
        metrics = telemetry_hook.get_metrics(limit=30)
        return {"events": metrics}

    # --- Multiplexed WebSocket ---

    @app.websocket("/ws/dashboard")
    async def ws_dashboard(websocket: WebSocket):
        """Multiplexed WebSocket for all dashboard real-time data.

        Protocol:
          Client -> {"channel":"subscribe","topics":["messages","logs","telemetry","agents"]}
          Server -> {"channel":"<topic>","data":{...}}
        """
        if auth_token:
            provided = websocket.cookies.get("aethon_dash") or websocket.query_params.get("token", "")
            if provided != auth_token:
                await websocket.close(code=1008)
                return
        await websocket.accept()

        # Subscribe to event bus if available
        queue = None
        if event_bus:
            queue = event_bus.subscribe(maxsize=500)

        subscribed_topics = set()
        forward_task = None

        try:
            # Start forwarding events from the bus to the client
            if queue:
                forward_task = asyncio.create_task(
                    _forward_events(websocket, queue, subscribed_topics)
                )

            # Read client messages (subscriptions, config changes)
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    channel = msg.get("channel", "")

                    if channel == "subscribe":
                        topics = msg.get("topics", [])
                        subscribed_topics.update(topics)
                        logger.debug(f"WS client subscribed to: {topics}")

                except json.JSONDecodeError:
                    pass  # Ignore non-JSON messages

        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass  # server shutting down — not an error
        except Exception as e:
            logger.debug(f"WS dashboard error: {e}")
        finally:
            if forward_task:
                forward_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    pass
            if event_bus and queue:
                event_bus.unsubscribe(queue)


async def _forward_events(websocket, queue, subscribed_topics):
    """Forward events from the event bus queue to the WebSocket client.

    Only forwards events matching the client's subscribed topics.
    """
    try:
        while True:
            event = await queue.get()
            channel = event.get("channel", "")

            # Only forward if client subscribed to this topic
            if not subscribed_topics or channel in subscribed_topics:
                try:
                    await websocket.send_text(json.dumps(event))
                except Exception:
                    break  # WebSocket closed
    except asyncio.CancelledError:
        pass
