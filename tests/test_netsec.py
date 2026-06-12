"""Tests for the network-security gates (Phase 9A — aethon/gateway/netsec.py)."""

import pytest

from aethon.config import AethonConfig
from aethon.gateway.netsec import check_bind_security, is_loopback_host


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
