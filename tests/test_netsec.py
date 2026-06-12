"""Tests for the network-security gates (Phase 9A — aethon/gateway/netsec.py)."""

import pytest

from aethon.config import AethonConfig
from aethon.gateway.netsec import (
    allowlist_gaps,
    check_bind_security,
    is_loopback_host,
    origin_allowed,
)


# --- is_loopback_host -------------------------------------------------------


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "127.0.0.5", "::1", "localhost", "LOCALHOST", " 127.0.0.1 "],
)
def test_loopback_hosts(host):
    assert is_loopback_host(host) is True


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "192.168.1.5", "10.0.0.1", "example.com", "myhost.local", "", "::"],
)
def test_non_loopback_hosts(host):
    # Non-IP hostnames count as exposed on purpose (when in doubt, require auth).
    assert is_loopback_host(host) is False


# --- check_bind_security ----------------------------------------------------


def _cfg(host: str = "127.0.0.1", token: str = "", webchat_enabled: bool = True):
    cfg = AethonConfig()
    cfg.channels.webchat.enabled = webchat_enabled
    cfg.channels.webchat.host = host
    cfg.dashboard.auth_token = token
    return cfg


def test_loopback_without_token_ok():
    ok, msg = check_bind_security(_cfg())
    assert ok is True


def test_nonloopback_without_token_refused():
    ok, msg = check_bind_security(_cfg(host="0.0.0.0"))
    assert ok is False
    # The message must name the exact config keys so the user can act on it.
    assert "dashboard.auth_token" in msg
    assert "channels.webchat.host" in msg
    assert "AETHON_DASHBOARD_TOKEN" in msg
    assert "--insecure-bind" in msg


def test_nonloopback_with_token_ok():
    ok, _ = check_bind_security(_cfg(host="0.0.0.0", token="secret"))
    assert ok is True


def test_whitespace_token_counts_as_empty():
    ok, _ = check_bind_security(_cfg(host="0.0.0.0", token="   "))
    assert ok is False


def test_webchat_disabled_no_http_surface_ok():
    ok, _ = check_bind_security(_cfg(host="0.0.0.0", webchat_enabled=False))
    assert ok is True


# --- origin_allowed (S2) ------------------------------------------------------


def test_origin_absent_passes():
    """Non-browser clients (curl, Python websockets) send no Origin — the token
    is their gate (explicit design decision, design doc §6)."""
    assert origin_allowed(None, "localhost:18790", []) is True
    assert origin_allowed("", "localhost:18790", []) is True


def test_origin_same_host_passes():
    assert origin_allowed("http://localhost:18790", "localhost:18790", []) is True
    assert origin_allowed("http://testserver", "testserver", []) is True
    # TLS reverse proxy: both Origin and Host omit the default port.
    assert origin_allowed("https://example.com", "example.com", []) is True


def test_origin_mismatch_rejected():
    assert origin_allowed("http://evil.example", "localhost:18790", []) is False
    # Same hostname, different port — still a different origin.
    assert origin_allowed("http://localhost:9999", "localhost:18790", []) is False


def test_origin_null_rejected():
    """'Origin: null' (sandboxed iframe, file://) has no netloc — rejected."""
    assert origin_allowed("null", "localhost:18790", []) is False


def test_origin_configured_allowlist_passes():
    allowed = ["https://chat.example.com"]
    assert origin_allowed("https://chat.example.com", "localhost:18790", allowed) is True
    assert origin_allowed("https://other.example.com", "localhost:18790", allowed) is False


def test_origin_allowlist_normalizes_trailing_slash_and_case():
    allowed = ["https://Chat.Example.com/"]
    assert origin_allowed("https://chat.example.com", "x", allowed) is True


# --- allowlist_gaps (S5) ------------------------------------------------------


def test_allowlist_gaps_disabled_bots_silent():
    assert allowlist_gaps(AethonConfig()) == []


def test_allowlist_gaps_enabled_bot_empty_allowlist():
    """Covers the wizard-skip path: bot enabled, restrict-confirm declined."""
    cfg = AethonConfig()
    cfg.channels.telegram.enabled = True
    assert allowlist_gaps(cfg) == ["telegram"]


def test_allowlist_gaps_populated_allowlist_ok():
    cfg = AethonConfig()
    cfg.channels.telegram.enabled = True
    cfg.security.allowed_senders = {"telegram": ["123"]}
    assert allowlist_gaps(cfg) == []


def test_allowlist_gaps_multiple_channels():
    cfg = AethonConfig()
    cfg.channels.telegram.enabled = True
    cfg.channels.whatsapp.enabled = True
    cfg.security.allowed_senders = {"telegram": ["123"]}
    assert allowlist_gaps(cfg) == ["whatsapp"]
