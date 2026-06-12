"""Single-instance guard (Phase 9B / H6).

Two gateways sharing one ``~/.aethon`` corrupt each other — double writes, and
Telegram's getUpdates rejects a second long-poller. An exclusive ``flock`` on a
pid file makes a second ``aethon start`` refuse to run with a clear message.

Unix-only (flock); on platforms without ``fcntl`` the guard is a no-op.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("aethon.gateway")


class SingleInstanceLock:
    """An advisory exclusive lock on a pid file, held for the process lifetime."""

    def __init__(self, path: Path):
        self.path = Path(path).expanduser()
        self._fd: int | None = None

    def acquire(self) -> tuple[bool, str | None]:
        """Try to take the lock.

        Returns ``(True, None)`` on success (and keeps the fd open), or
        ``(False, other_pid)`` when another instance holds it. On a platform
        without ``fcntl`` it succeeds (no guard available).
        """
        try:
            import fcntl
        except ImportError:  # pragma: no cover - non-Unix
            return True, None

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            try:
                other = os.read(fd, 32).decode(errors="replace").strip() or "?"
            except OSError:
                other = "?"
            os.close(fd)
            return False, other
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        os.fsync(fd)
        self._fd = fd
        return True, None

    def release(self) -> None:
        """Release the lock (best-effort)."""
        if self._fd is None:
            return
        try:
            import fcntl

            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except Exception:  # pragma: no cover - best effort
            pass
        try:
            os.close(self._fd)
        except OSError:  # pragma: no cover
            pass
        self._fd = None
