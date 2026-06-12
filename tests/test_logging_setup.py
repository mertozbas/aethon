"""Tests for root file logging (Phase 9B / H9)."""

import logging

import pytest

from aethon.config import AethonConfig, PathsConfig, LoggingConfig
from aethon.__main__ import _setup_file_logging


@pytest.fixture
def _clean_root():
    root = logging.getLogger()
    before = list(root.handlers)
    before_level = root.level
    aethon_before = logging.getLogger("aethon").level
    yield
    # Remove any handler we added; restore levels.
    for h in list(root.handlers):
        if getattr(h, "_aethon_file", False):
            root.removeHandler(h)
            h.close()
    root.handlers[:] = before
    root.setLevel(before_level)
    logging.getLogger("aethon").setLevel(aethon_before)


def _cfg(tmp_path, **logging_kw):
    return AethonConfig(
        paths=PathsConfig(logs=str(tmp_path / "logs")),
        logging=LoggingConfig(**logging_kw),
    )


def test_third_party_error_reaches_file(tmp_path, _clean_root):
    _setup_file_logging(_cfg(tmp_path))
    # A non-aethon logger at ERROR must land in the file (root-attached handler).
    logging.getLogger("strands.models.openai").error("bad key 401")
    logging.getLogger("aethon.test").info("aethon info line")
    for h in logging.getLogger().handlers:
        if getattr(h, "_aethon_file", False):
            h.flush()
    log = (tmp_path / "logs" / "aethon.log").read_text()
    assert "bad key 401" in log            # third-party error captured
    assert "aethon info line" in log       # aethon INFO captured


def test_third_party_info_is_filtered(tmp_path, _clean_root):
    _setup_file_logging(_cfg(tmp_path))
    logging.getLogger("uvicorn.access").info("noisy access line")
    for h in logging.getLogger().handlers:
        if getattr(h, "_aethon_file", False):
            h.flush()
    log = (tmp_path / "logs" / "aethon.log").read_text()
    assert "noisy access line" not in log  # below the WARNING third-party floor


def test_disabled_skips_setup(tmp_path, _clean_root):
    _setup_file_logging(_cfg(tmp_path, enabled=False))
    assert not (tmp_path / "logs" / "aethon.log").exists()
    assert not any(
        getattr(h, "_aethon_file", False) for h in logging.getLogger().handlers
    )


def test_level_knob_controls_aethon_level(tmp_path, _clean_root):
    _setup_file_logging(_cfg(tmp_path, level="DEBUG"))
    assert logging.getLogger("aethon").level == logging.DEBUG
