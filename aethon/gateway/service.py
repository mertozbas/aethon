"""Run-at-boot service units (Phase 9B / H11).

Renders a launchd plist (macOS) or a systemd user unit (Linux) that keeps
``aethon start`` running, restarting on failure, with stdout/err redirected to
``~/.aethon/logs/``. Pure renderers + an installer the CLI calls.
"""

import sys
from pathlib import Path

LABEL = "com.aethon.gateway"


def render_launchd(exe: str, logs_dir: str) -> str:
    """A launchd plist that KeepAlive-restarts ``aethon start`` (macOS)."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>{exe}</string><string>start</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key>
  <dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardOutPath</key><string>{logs_dir}/service.out.log</string>
  <key>StandardErrorPath</key><string>{logs_dir}/service.err.log</string>
</dict>
</plist>
"""


def render_systemd(exe: str, logs_dir: str) -> str:
    """A systemd user unit that Restart=on-failure ``aethon start`` (Linux)."""
    return f"""[Unit]
Description=AETHON personal assistant gateway
After=network-online.target

[Service]
ExecStart={exe} start
Restart=on-failure
RestartSec=5
StandardOutput=append:{logs_dir}/service.out.log
StandardError=append:{logs_dir}/service.err.log

[Install]
WantedBy=default.target
"""


def install_service(logs_dir: str, platform: str | None = None) -> tuple[Path, str]:
    """Write the platform service unit. Returns ``(path, load_hint)``.

    Raises ``RuntimeError`` on an unsupported platform.
    """
    plat = platform or sys.platform
    exe = _aethon_exe()
    if plat == "darwin":
        path = Path("~/Library/LaunchAgents").expanduser() / f"{LABEL}.plist"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_launchd(exe, logs_dir))
        hint = f"launchctl load {path}"
    elif plat.startswith("linux"):
        path = Path("~/.config/systemd/user").expanduser() / "aethon.service"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_systemd(exe, logs_dir))
        hint = "systemctl --user daemon-reload && systemctl --user enable --now aethon"
    else:
        raise RuntimeError(
            f"Run-at-boot is supported on macOS and Linux, not {plat!r}."
        )
    return path, hint


def _aethon_exe() -> str:
    """Best path to the aethon CLI for the unit's ExecStart."""
    import shutil

    return shutil.which("aethon") or f"{sys.executable} -m aethon"
