"""Tests for the macOS menu-bar launcher helpers (GUI-independent)."""

import os

from aethon.launcher import macos_menubar as mb


def test_pid_roundtrip(tmp_path, monkeypatch):
    pid_file = tmp_path / ".menubar_server.pid"
    monkeypatch.setattr(mb, "PID_FILE", pid_file)
    assert mb._read_pid() is None  # absent
    pid_file.write_text("4321")
    assert mb._read_pid() == 4321
    pid_file.write_text("garbage")
    assert mb._read_pid() is None  # unparseable -> None


def test_is_running():
    assert mb._is_running(os.getpid()) is True
    assert mb._is_running(None) is False
    assert mb._is_running(2_000_000_000) is False  # almost certainly no such pid


def test_start_server_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(mb, "PID_FILE", tmp_path / ".pid")
    monkeypatch.setattr(mb, "_read_pid", lambda: 1234)
    monkeypatch.setattr(mb, "_is_running", lambda pid: True)
    spawned = {"called": False}
    monkeypatch.setattr(mb.subprocess, "Popen", lambda *a, **k: spawned.__setitem__("called", True))
    # already running -> returns existing pid, no new process
    assert mb.start_server() == 1234
    assert spawned["called"] is False


def test_stop_server_when_not_running(tmp_path, monkeypatch):
    monkeypatch.setattr(mb, "PID_FILE", tmp_path / ".pid")
    monkeypatch.setattr(mb, "_read_pid", lambda: None)
    # no crash, returns None
    assert mb.stop_server() is None


def test_main_without_rumps_returns_1():
    # rumps is not installed in the test env -> graceful exit code 1
    import importlib.util
    if importlib.util.find_spec("rumps") is None:
        assert mb.main() == 1
