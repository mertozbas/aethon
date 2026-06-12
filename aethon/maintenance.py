"""Disk retention + reporting (Phase 9B / H7).

Session-reset backups (``cleared/batch_*``) and recordings grow without bound.
``apply_retention`` prunes them at boot; ``disk_report`` powers the
``aethon doctor`` disk section. All best-effort — never fatal.
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger("aethon.maintenance")


def _batch_num(p: Path) -> int:
    try:
        return int(p.name.split("_")[-1])
    except (ValueError, IndexError):
        return -1


def _prune_cleared(sessions_root: Path, keep: int) -> int:
    """Keep only the newest ``keep`` cleared/batch_* dirs per session."""
    if keep <= 0 or not sessions_root.exists():
        return 0
    removed = 0
    for cleared in sessions_root.glob("**/cleared"):
        if not cleared.is_dir():
            continue
        batches = sorted(
            (p for p in cleared.glob("batch_*") if p.is_dir()),
            key=_batch_num,
        )
        for old in batches[:-keep] if len(batches) > keep else []:
            try:
                _rmtree(old)
                removed += 1
            except OSError as e:
                logger.warning(f"Retention: could not remove {old}: {e}")
    return removed


def _prune_recordings(recordings_dir: Path, keep: int, max_age_days: int) -> int:
    """Cap recording archives by count (newest ``keep``) and optional age."""
    if not recordings_dir.exists():
        return 0
    files = sorted(
        (p for p in recordings_dir.glob("*.zip") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
    )
    doomed = set()
    if keep > 0 and len(files) > keep:
        doomed.update(files[:-keep])
    if max_age_days > 0:
        cutoff = time.time() - max_age_days * 86400
        doomed.update(p for p in files if p.stat().st_mtime < cutoff)
    removed = 0
    for p in doomed:
        try:
            p.unlink()
            removed += 1
        except OSError as e:
            logger.warning(f"Retention: could not remove {p}: {e}")
    return removed


def apply_retention(config) -> dict:
    """Prune old cleared-batches and recordings per the retention config."""
    ret = getattr(config, "retention", None)
    if ret is not None and not getattr(ret, "enabled", True):
        return {"cleared": 0, "recordings": 0}
    sessions_root = Path(config.paths.sessions).expanduser()
    recordings_dir = Path(config.paths.recordings).expanduser()
    cleared = _prune_cleared(sessions_root, getattr(ret, "cleared_keep", 10))
    recs = _prune_recordings(
        recordings_dir,
        getattr(ret, "recordings_keep", 20),
        getattr(ret, "recordings_max_age_days", 0),
    )
    if cleared or recs:
        logger.info(f"Retention: removed {cleared} cleared batch(es), {recs} recording(s)")
    return {"cleared": cleared, "recordings": recs}


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def disk_report(config) -> list[tuple[str, int]]:
    """``[(label, bytes)]`` for the main on-disk state areas (aethon doctor)."""
    paths = config.paths
    items = [
        ("sessions", Path(paths.sessions).expanduser()),
        ("recordings", Path(paths.recordings).expanduser()),
        ("logs", Path(paths.logs).expanduser()),
        ("memory.sqlite", Path(paths.memory_db).expanduser()),
        ("workspace", Path(paths.workspace).expanduser()),
    ]
    return [(label, _dir_size(p)) for label, p in items]


def human_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def _rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path)


# --- backup (H10) ----------------------------------------------------------


def _sqlite_backup(src: Path, dst: Path) -> None:
    """Consistent live copy of a SQLite DB (safe while AETHON is running)."""
    import sqlite3

    s = sqlite3.connect(str(src))
    d = sqlite3.connect(str(dst))
    try:
        with d:
            s.backup(d)
    finally:
        s.close()
        d.close()


def create_backup(home: Path, output: Path) -> Path:
    """Archive ``~/.aethon`` to a ``.tar.gz`` (H10).

    SQLite DBs are copied via the live-safe backup API so the archive is
    consistent even while the gateway runs; ``logs/`` is skipped. Returns the
    output path.
    """
    import tarfile
    import tempfile

    home = Path(home).expanduser()
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with tarfile.open(output, "w:gz") as tar:
            for p in sorted(home.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(home)
                if rel.parts and rel.parts[0] == "logs":
                    continue  # transient — don't bloat the backup
                if p == output:
                    continue  # never archive the archive itself
                if p.suffix == ".sqlite":
                    consistent = tmp / rel.name
                    try:
                        _sqlite_backup(p, consistent)
                        tar.add(consistent, arcname=str(rel))
                        continue
                    except Exception as e:
                        logger.warning(f"Live SQLite backup failed for {rel}: {e}")
                tar.add(p, arcname=str(rel))
    return output
