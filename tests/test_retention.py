"""Tests for disk retention + reporting (Phase 9B / H7)."""

import time

from aethon.config import AethonConfig, PathsConfig, RetentionConfig
from aethon.maintenance import apply_retention, disk_report, human_bytes


def _cfg(tmp_path, **retention_kw):
    return AethonConfig(
        paths=PathsConfig(
            sessions=str(tmp_path / "sessions"),
            recordings=str(tmp_path / "recordings"),
            logs=str(tmp_path / "logs"),
            memory_db=str(tmp_path / "memory.sqlite"),
            workspace=str(tmp_path / "ws"),
        ),
        retention=RetentionConfig(**retention_kw),
    )


def test_cleared_batches_pruned_to_newest_n(tmp_path):
    agent = tmp_path / "sessions" / "session_s1" / "agents" / "agent_main" / "cleared"
    agent.mkdir(parents=True)
    for i in range(15):
        b = agent / f"batch_{i}"
        b.mkdir()
        (b / "message_0.json").write_text("{}")

    res = apply_retention(_cfg(tmp_path, cleared_keep=5))
    assert res["cleared"] == 10  # 15 - 5 kept
    remaining = sorted(int(p.name.split("_")[1]) for p in agent.glob("batch_*"))
    assert remaining == [10, 11, 12, 13, 14]  # the newest five


def test_recordings_capped_by_count(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    for i in range(8):
        f = rec / f"rec_{i}.zip"
        f.write_text("x")
        # stagger mtimes so "newest" is well-defined
        os_time = time.time() - (8 - i)
        import os

        os.utime(f, (os_time, os_time))

    res = apply_retention(_cfg(tmp_path, recordings_keep=3))
    assert res["recordings"] == 5
    assert len(list(rec.glob("*.zip"))) == 3


def test_recordings_age_cap(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    import os

    old = rec / "old.zip"
    old.write_text("x")
    old_t = time.time() - 40 * 86400
    os.utime(old, (old_t, old_t))
    new = rec / "new.zip"
    new.write_text("x")

    apply_retention(_cfg(tmp_path, recordings_keep=0, recordings_max_age_days=30))
    assert not old.exists()
    assert new.exists()


def test_retention_disabled_is_noop(tmp_path):
    agent = tmp_path / "sessions" / "session_s1" / "agents" / "agent_main" / "cleared"
    agent.mkdir(parents=True)
    for i in range(5):
        (agent / f"batch_{i}").mkdir()
    res = apply_retention(_cfg(tmp_path, enabled=False))
    assert res == {"cleared": 0, "recordings": 0}
    assert len(list(agent.glob("batch_*"))) == 5


def test_disk_report_lists_areas(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "f.json").write_text("x" * 100)
    report = dict(disk_report(_cfg(tmp_path)))
    assert "sessions" in report and report["sessions"] >= 100
    assert "recordings" in report and "memory.sqlite" in report


def test_human_bytes():
    assert human_bytes(0) == "0B"
    assert human_bytes(1536) == "1.5KB"
    assert human_bytes(5 * 1024 * 1024) == "5.0MB"
