"""macOS menu-bar launcher for AETHON.

A minimal ``rumps`` menu-bar app that starts/stops the AETHON gateway as a child
process and offers quick links. Runs as a normal user process (no root); the
spawned server enforces all the usual security hooks — the launcher is not a
security boundary itself.

Requires the ``[launcher-macos]`` extra (rumps). Run via ``aethon-menubar``.
"""

import os
import signal
import subprocess
import sys
import webbrowser
from pathlib import Path

PID_FILE = Path.home() / ".aethon" / ".menubar_server.pid"


def _read_pid():
    """Return the recorded server PID, or None."""
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def _is_running(pid) -> bool:
    """True if a process with this PID is alive."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)  # signal 0 just checks existence
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except OSError:
        return False


def start_server(config_path: str = "~/.aethon/config.yaml"):
    """Spawn the AETHON gateway as a detached child; record its PID. Idempotent."""
    existing = _read_pid()
    if _is_running(existing):
        return existing
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "aethon", "start", "-c", config_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    return proc.pid


def stop_server():
    """Terminate the recorded server (SIGTERM) and clear the PID file."""
    pid = _read_pid()
    if _is_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    try:
        PID_FILE.unlink()
    except OSError:
        pass
    return pid


def open_webchat(port: int = 18790) -> None:
    webbrowser.open(f"http://localhost:{port}")


def open_settings(config_path: str = "~/.aethon/config.yaml") -> None:
    path = Path(config_path).expanduser()
    try:
        subprocess.Popen(["open", str(path)])  # macOS default editor
    except Exception:
        pass


def _build_app(rumps):
    """Construct the rumps menu-bar app (rumps passed in to keep import lazy)."""

    class AethonMenuBar(rumps.App):
        def __init__(self):
            super().__init__("AETHON", title="\U0001FAB6")  # feather glyph
            self.menu = ["Start Server", "Stop Server", "Open WebChat", "Settings"]

        @rumps.clicked("Start Server")
        def _start(self, _):
            pid = start_server()
            rumps.notification("AETHON", "Server", f"Running (pid {pid})")

        @rumps.clicked("Stop Server")
        def _stop(self, _):
            stop_server()
            rumps.notification("AETHON", "Server", "Stopped")

        @rumps.clicked("Open WebChat")
        def _webchat(self, _):
            open_webchat()

        @rumps.clicked("Settings")
        def _settings(self, _):
            open_settings()

    return AethonMenuBar()


def main() -> int:
    try:
        import rumps
    except ImportError:
        print(
            "aethon-menubar requires the [launcher-macos] extra: "
            "pip install aethon-ai[launcher-macos]",
            file=sys.stderr,
        )
        return 1
    _build_app(rumps).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
