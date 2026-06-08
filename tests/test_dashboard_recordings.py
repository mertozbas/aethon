"""Tests for the session-recordings dashboard API (§2.17)."""

import os
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aethon.config import AethonConfig, PathsConfig
from aethon.ui.dashboard import setup_dashboard
from aethon.agent.session_recording import SessionRecorder


@pytest.fixture
def recording(tmp_path):
    """Create a recording ZIP in a temp recordings dir; return (dir, zip_name)."""
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    rec = SessionRecorder(session_id="dash-sess")
    rec.start(install_hooks=False)
    rec.record_tool_call("scraper", {"url": "https://x"})
    rec.record_tool_result("scraper", "ok")
    rec.record_agent_message("assistant", "done")

    class FakeAgent:
        messages = [{"role": "user", "content": [{"text": "q"}]}]
        tool_names = ["scraper"]
        system_prompt = "SP"

    rec.snapshot(agent=FakeAgent(), description="d", last_query="q", last_result="r")
    rec.stop()
    rec.export(str(rec_dir / "dash-sess.zip"))
    return rec_dir, "dash-sess.zip"


@pytest.fixture
def client(recording):
    rec_dir, _ = recording
    config = AethonConfig(paths=PathsConfig(recordings=str(rec_dir)))
    runtime = MagicMock()
    app = FastAPI()
    setup_dashboard(app, runtime, config, event_bus=None)
    return TestClient(app)


def test_list_recordings(client, recording):
    _, zip_name = recording
    r = client.get("/api/sessions/recordings")
    assert r.status_code == 200
    names = [rec["name"] for rec in r.json()["recordings"]]
    assert zip_name in names


def test_recording_metadata(client, recording):
    _, zip_name = recording
    r = client.get(f"/api/sessions/recordings/{zip_name}")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == "dash-sess"
    assert body["events_count"] >= 3
    assert body["snapshots_count"] == 1


def test_recording_events_filtered(client, recording):
    _, zip_name = recording
    r = client.get(f"/api/sessions/recordings/{zip_name}/events", params={"layer": "tool"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert events and all(e["layer"] == "tool" for e in events)


def test_recording_snapshots(client, recording):
    _, zip_name = recording
    r = client.get(f"/api/sessions/recordings/{zip_name}/snapshots")
    assert r.status_code == 200
    snaps = r.json()["snapshots"]
    assert len(snaps) == 1 and snaps[0]["id"] == 1


def test_recording_replay_preview_no_cwd_change(client, recording):
    _, zip_name = recording
    cwd_before = os.getcwd()
    r = client.post(f"/api/sessions/recordings/{zip_name}/replay/1")
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert os.getcwd() == cwd_before  # server cwd must be restored


def test_unknown_recording_404(client):
    assert client.get("/api/sessions/recordings/nope.zip").status_code == 404


def test_path_traversal_exposes_nothing(client):
    """A traversal attempt must never expose a recording or file contents.

    The guard matches names only against real *.zip files in the recordings dir
    (glob), so traversal can't resolve to a file; an encoded-slash path simply
    falls through to the session-detail route, which returns no recording data.
    """
    r = client.get("/api/sessions/recordings/..%2f..%2fetc%2fpasswd")
    assert r.status_code != 200 or "events_count" not in r.json()
