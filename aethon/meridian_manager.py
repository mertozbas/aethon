"""Manage the Meridian proxy lifecycle.

When the default ``meridian`` provider is selected, aethon can start the Meridian
proxy automatically — as a detached background process — so the user never has to
run it by hand or keep a terminal open. Meridian bridges the Claude Code SDK to
the Anthropic API, drawing on the user's Claude Max subscription.

The proxy is started from a neutral working directory (``~/.aethon``) so aethon's
context comes only from its own workspace, not from whatever project a manually
started Meridian happened to inherit. https://github.com/rynfar/meridian
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

DEFAULT_BASE_URL = "http://127.0.0.1:3456"

# Where the `meridian` binary commonly lives (npm global, Homebrew, etc.).
_BINARY_CANDIDATES = (
    "~/.npm-global/bin/meridian",
    "/opt/homebrew/bin/meridian",
    "/usr/local/bin/meridian",
    "~/.local/bin/meridian",
)


def find_meridian_binary() -> Optional[str]:
    """Locate the meridian executable on PATH or in common install locations."""
    on_path = shutil.which("meridian")
    if on_path:
        return on_path
    for candidate in _BINARY_CANDIDATES:
        path = Path(candidate).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return None


def is_running(base_url: str = DEFAULT_BASE_URL, timeout: float = 3.0) -> bool:
    """Return True if Meridian answers /health at base_url."""
    try:
        from strands_meridian import is_available

        return is_available(base_url, timeout=timeout)
    except Exception:
        return False


def _env_for(base_url: str) -> dict:
    """Build env overrides so a non-default base_url maps to MERIDIAN_HOST/PORT."""
    env = dict(os.environ)
    parsed = urlparse(base_url)
    if parsed.hostname and parsed.hostname not in ("127.0.0.1", "localhost"):
        env["MERIDIAN_HOST"] = parsed.hostname
    if parsed.port and parsed.port != 3456:
        env["MERIDIAN_PORT"] = str(parsed.port)
    return env


def ensure_running(
    base_url: str = DEFAULT_BASE_URL,
    *,
    cwd: Optional[str] = None,
    log_path: Optional[str] = None,
    start_timeout: float = 30.0,
) -> Tuple[bool, str]:
    """Ensure Meridian is reachable, starting it in the background if needed.

    Args:
        base_url: Where Meridian should answer.
        cwd: Working directory for the spawned proxy (default ``~/.aethon`` — a
            neutral dir, so aethon's context isn't polluted by a project CLAUDE.md).
        log_path: Where to append Meridian's output (default ``~/.aethon/logs/meridian.log``).
        start_timeout: Seconds to wait for the freshly started proxy to become healthy.

    Returns:
        (running, message). ``running`` is False with an actionable message if the
        binary is missing or the proxy fails to come up.
    """
    if is_running(base_url):
        return True, "already running"

    binary = find_meridian_binary()
    if not binary:
        return False, (
            "Meridian is not installed. Install it with "
            "`npm install -g @rynfar/meridian`, then run `claude login`."
        )

    work_dir = Path(cwd).expanduser() if cwd else Path.home() / ".aethon"
    work_dir.mkdir(parents=True, exist_ok=True)
    log = Path(log_path).expanduser() if log_path else work_dir / "logs" / "meridian.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    pid_file = work_dir / "meridian.pid"

    _spawn_detached(binary, work_dir, log, _env_for(base_url), pid_file)

    deadline = time.time() + start_timeout
    while time.time() < deadline:
        if is_running(base_url, timeout=2.0):
            pid = pid_file.read_text().strip() if pid_file.exists() else "?"
            return True, f"started in the background (pid {pid}; logs: {log})"
        time.sleep(0.5)
    return False, (
        f"Meridian did not become healthy within {int(start_timeout)}s — check {log} "
        f"(you may need to run `claude login` first)."
    )


def _spawn_detached(binary: str, work_dir: Path, log: Path, env: dict, pid_file: Path) -> None:
    """Start ``binary`` as a fully-detached background daemon.

    On POSIX this double-forks so the daemon is reparented to init (pid 1) — it
    survives aethon exiting, being killed, or its whole process tree being torn
    down. The daemon writes its own pid to ``pid_file`` before exec.
    """
    if os.name == "nt":  # pragma: no cover — Windows fallback
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        with open(log, "a") as logf:
            proc = subprocess.Popen(
                [binary], cwd=str(work_dir), stdout=logf, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, env=env, creationflags=flags,
            )
        pid_file.write_text(str(proc.pid))
        return

    pid = os.fork()
    if pid > 0:
        os.waitpid(pid, 0)  # reap the short-lived intermediate child
        return

    # --- intermediate child ---
    try:
        os.setsid()
        if os.fork() > 0:
            os._exit(0)  # intermediate exits → grandchild is orphaned to init
        # --- grandchild: becomes the Meridian daemon ---
        os.chdir(str(work_dir))
        try:
            pid_file.write_text(str(os.getpid()))
        except OSError:
            pass
        devnull = os.open(os.devnull, os.O_RDONLY)
        logfd = os.open(str(log), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(devnull, 0)
        os.dup2(logfd, 1)
        os.dup2(logfd, 2)
        for key, value in env.items():
            os.environ[key] = value
        os.execv(binary, [binary])
    except BaseException:
        os._exit(127)
