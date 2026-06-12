"""Tests for the single-instance guard (Phase 9B / H6)."""

import os

from aethon.gateway.single_instance import SingleInstanceLock


def test_first_acquires_second_refused(tmp_path):
    path = tmp_path / "aethon.pid"
    a = SingleInstanceLock(path)
    b = SingleInstanceLock(path)

    ok_a, other_a = a.acquire()
    assert ok_a is True and other_a is None
    # The pid file records our pid.
    assert path.read_text().strip() == str(os.getpid())

    ok_b, other_b = b.acquire()  # second instance on the same file
    assert ok_b is False
    assert other_b == str(os.getpid())  # tells you who holds it

    a.release()
    # After release, a fresh instance can acquire.
    ok_c, _ = b.acquire()
    assert ok_c is True
    b.release()


def test_release_is_idempotent(tmp_path):
    lock = SingleInstanceLock(tmp_path / "x.pid")
    lock.release()  # never acquired — must not raise
    ok, _ = lock.acquire()
    assert ok is True
    lock.release()
    lock.release()  # double release — must not raise
