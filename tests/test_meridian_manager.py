"""Tests for Meridian lifecycle management (auto-start)."""

import aethon.meridian_manager as mm
from aethon.config import AethonConfig


def test_config_auto_start_default_true():
    assert AethonConfig().meridian.auto_start is True


def test_find_binary_prefers_path(monkeypatch):
    monkeypatch.setattr(mm.shutil, "which", lambda name: "/usr/local/bin/meridian")
    assert mm.find_meridian_binary() == "/usr/local/bin/meridian"


def test_find_binary_none_when_absent(monkeypatch):
    monkeypatch.setattr(mm.shutil, "which", lambda name: None)
    monkeypatch.setattr(mm, "_BINARY_CANDIDATES", ())
    assert mm.find_meridian_binary() is None


def test_env_for_custom_base_url():
    env = mm._env_for("http://192.168.1.5:9999")
    assert env["MERIDIAN_HOST"] == "192.168.1.5"
    assert env["MERIDIAN_PORT"] == "9999"


def test_env_for_default_adds_nothing():
    env = mm._env_for("http://127.0.0.1:3456")
    assert "MERIDIAN_HOST" not in env
    assert "MERIDIAN_PORT" not in env


def test_ensure_running_already_up(monkeypatch):
    monkeypatch.setattr(mm, "is_running", lambda *a, **k: True)
    ok, msg = mm.ensure_running()
    assert ok is True
    assert "already running" in msg


def test_ensure_running_binary_missing(monkeypatch):
    monkeypatch.setattr(mm, "is_running", lambda *a, **k: False)
    monkeypatch.setattr(mm, "find_meridian_binary", lambda: None)
    ok, msg = mm.ensure_running()
    assert ok is False
    assert "npm install -g @rynfar/meridian" in msg


def test_ensure_running_starts_in_background(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_is_running(base_url=mm.DEFAULT_BASE_URL, timeout=3.0):
        calls["n"] += 1
        return calls["n"] > 1  # down on the initial check, healthy after "start"

    def fake_spawn(binary, work_dir, log, env, pid_file):
        pid_file.write_text("4242")  # the daemon writes its own pid before exec

    monkeypatch.setattr(mm, "is_running", fake_is_running)
    monkeypatch.setattr(mm, "find_meridian_binary", lambda: "/fake/meridian")
    monkeypatch.setattr(mm, "_spawn_detached", fake_spawn)

    ok, msg = mm.ensure_running(cwd=str(tmp_path), log_path=str(tmp_path / "m.log"))
    assert ok is True
    assert "started in the background" in msg
    assert (tmp_path / "meridian.pid").read_text().strip() == "4242"


def test_ensure_running_times_out_when_unhealthy(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "is_running", lambda *a, **k: False)
    monkeypatch.setattr(mm, "find_meridian_binary", lambda: "/fake/meridian")
    monkeypatch.setattr(mm, "_spawn_detached", lambda *a, **k: None)

    ok, msg = mm.ensure_running(cwd=str(tmp_path), log_path=str(tmp_path / "m.log"), start_timeout=0.2)
    assert ok is False
    assert "did not become healthy" in msg
