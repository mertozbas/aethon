"""Tests for backup (H10) and run-at-boot service (H11)."""

import sqlite3
import tarfile

import pytest

from aethon.maintenance import create_backup
from aethon.gateway.service import (
    LABEL,
    install_service,
    render_launchd,
    render_systemd,
)


# --- H10: backup -----------------------------------------------------------


def test_create_backup_includes_files_skips_logs(tmp_path):
    home = tmp_path / ".aethon"
    (home / "logs").mkdir(parents=True)
    (home / "logs" / "aethon.log").write_text("noise")
    (home / "config.yaml").write_text("model:\n  provider: ollama\n")
    (home / "workspace").mkdir()
    (home / "workspace" / "SOUL.md").write_text("kişilik")

    out = create_backup(home, tmp_path / "backup.tar.gz")
    assert out.exists()
    with tarfile.open(out) as tar:
        names = tar.getnames()
    assert "config.yaml" in names
    assert "workspace/SOUL.md" in names
    assert not any(n.startswith("logs") for n in names)  # logs skipped


def test_create_backup_sqlite_is_consistent(tmp_path):
    home = tmp_path / ".aethon"
    home.mkdir()
    db = home / "memory.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE t (x int)")
    con.execute("INSERT INTO t VALUES (42)")
    con.commit()
    con.close()

    out = create_backup(home, tmp_path / "b.tar.gz")
    # Extract the DB and confirm the row survived (live-safe .backup copy).
    with tarfile.open(out) as tar:
        tar.extract("memory.sqlite", path=tmp_path / "restored", filter="data")
    rcon = sqlite3.connect(str(tmp_path / "restored" / "memory.sqlite"))
    assert rcon.execute("SELECT x FROM t").fetchone()[0] == 42
    rcon.close()


# --- H11: service renderers ------------------------------------------------


def test_render_launchd_has_keepalive_and_logs():
    plist = render_launchd("/usr/local/bin/aethon", "/home/u/.aethon/logs")
    assert LABEL in plist
    assert "KeepAlive" in plist
    assert "/usr/local/bin/aethon" in plist and "<string>start</string>" in plist
    assert "/home/u/.aethon/logs/service.err.log" in plist


def test_render_systemd_restart_on_failure():
    unit = render_systemd("/usr/bin/aethon", "/home/u/.aethon/logs")
    assert "Restart=on-failure" in unit
    assert "ExecStart=/usr/bin/aethon start" in unit
    assert "append:/home/u/.aethon/logs/service.out.log" in unit


def test_install_service_macos(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path, hint = install_service(str(tmp_path / "logs"), platform="darwin")
    assert path.exists() and path.suffix == ".plist"
    assert "launchctl load" in hint


def test_install_service_linux(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    path, hint = install_service(str(tmp_path / "logs"), platform="linux")
    assert path.name == "aethon.service"
    assert "systemctl --user" in hint


def test_install_service_unsupported_platform():
    with pytest.raises(RuntimeError, match="macOS and Linux"):
        install_service("/tmp/logs", platform="win32")
