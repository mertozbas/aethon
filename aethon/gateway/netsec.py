"""Network-security gates for the gateway (Phase 9A).

Pure, unit-testable check functions shared by the CLI (`aethon start`) and
``AethonGateway``. Doctrine: deny by default, fail closed at startup — a
misconfigured network surface is refused at boot, not discovered at attack time.
See docs/development/PHASE-9A-SECURITY.md.
"""

import ipaddress


def is_loopback_host(host: str) -> bool:
    """True when ``host`` is a loopback bind (127.0.0.0/8, ::1, localhost).

    Non-IP hostnames (e.g. ``myhost.local``) are treated as NON-loopback on
    purpose: when in doubt, the bind is considered exposed and auth is required.
    """
    host = (host or "").strip().lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_bind_security(config) -> tuple[bool, str]:
    """Refuse a non-loopback HTTP bind without a shared auth token.

    Returns ``(ok, message)`` — mirrors the ``check_model_availability``
    boot-check pattern. Only relevant when the WebChat channel (the sole HTTP
    surface) is enabled.
    """
    webchat = config.channels.webchat
    if not webchat.enabled or is_loopback_host(webchat.host):
        return True, ""
    token = (config.dashboard.auth_token or "").strip()
    if token:
        return True, ""
    return False, (
        f"channels.webchat.host={webchat.host!r} binds beyond loopback but "
        "dashboard.auth_token is empty — every HTTP/WebSocket surface would be "
        "exposed unauthenticated. Set dashboard.auth_token (Docker: the "
        "AETHON_DASHBOARD_TOKEN environment variable), or pass --insecure-bind "
        "if an authenticating reverse proxy fronts this server."
    )
