"""Tests for CLIAdapter.ask_approval (Phase 9A / S6 — CLI answerable)."""

import asyncio
import builtins

from unittest.mock import MagicMock

from aethon.config import AethonConfig
from aethon.channels.cli import CLIAdapter
from aethon.channels.base import ApprovalRequest


def _adapter():
    return CLIAdapter(AethonConfig(), MagicMock())


def _request():
    return ApprovalRequest(
        interrupt_id="i1",
        tool="shell",
        parameters={"command": "rm -rf x"},
        message="'shell' calistirilmak isteniyor. Onayla?",
        session_id="cli:local",
        recipient_id="local",
    )


def test_cli_approval_yes(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "e")
    assert asyncio.run(_adapter().ask_approval(_request())) is True


def test_cli_approval_no(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "h")
    assert asyncio.run(_adapter().ask_approval(_request())) is False


def test_cli_approval_accepts_english_yes(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "yes")
    assert asyncio.run(_adapter().ask_approval(_request())) is True


def test_cli_approval_eof_denies(monkeypatch):
    def _raise(_prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", _raise)
    assert asyncio.run(_adapter().ask_approval(_request())) is False
