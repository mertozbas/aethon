"""Network-security gates for the gateway (Phase 9A).

Pure, unit-testable check functions shared by the CLI (`aethon start`) and
``AethonGateway``. Doctrine: deny by default, fail closed at startup — a
misconfigured network surface is refused at boot, not discovered at attack time.
See docs/development/PHASE-9A-SECURITY.md.
"""

import ipaddress
import secrets

from fastapi.responses import HTMLResponse, JSONResponse

# Deny-by-default HTTP gate (S1): everything on the shared app requires the
# token except these enumerated public surfaces.
#   /        — the chat page (UI only; its WebSocket is gated separately)
#   /health  — liveness probe (Docker HEALTHCHECK / load balancers)
PUBLIC_PATHS = frozenset({"/", "/health"})
# Prefixes:
#   /dashboard/static/ — SPA assets (shipped publicly in the package anyway;
#                        avoids racing the auth cookie on first SPA load)
#   /webhook/          — self-authenticating via HMAC; fails closed without a
#                        secret beyond loopback (S3)
PUBLIC_PREFIXES = ("/dashboard/static/", "/webhook/")


def provided_token(conn) -> str:
    """Client-supplied token from an HTTP request OR a WebSocket upgrade.

    Both are starlette ``HTTPConnection``s with the same accessors. Precedence:
    ``aethon_dash`` cookie, ``Authorization: Bearer``, ``?token=`` query param.
    """
    header = conn.headers.get("authorization", "")
    bearer = header[7:] if header[:7].lower() == "bearer " else ""
    return conn.cookies.get("aethon_dash") or bearer or conn.query_params.get("token", "")


def token_ok(conn, auth_token: str) -> bool:
    """True when no token is configured, or the connection supplies it."""
    token = (auth_token or "").strip()
    if not token:
        return True
    return secrets.compare_digest(provided_token(conn), token)


def install_auth_gate(app, auth_token: str) -> None:
    """Install the deny-by-default auth middleware on the shared app (S1).

    Empty token = no middleware = open — coherent only because
    ``check_bind_security`` refuses non-loopback binds without a token (S4).
    WebSocket endpoints gate themselves before ``accept()``: Starlette "http"
    middleware never sees upgrade requests.
    """
    token = (auth_token or "").strip()
    if not token:
        return

    @app.middleware("http")
    async def _auth_gate(request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        if not token_ok(request, token):
            if path == "/dashboard":
                return HTMLResponse(
                    "<html><body><h3>AETHON dashboard</h3><p>This dashboard is "
                    "protected. Open <code>/dashboard?token=YOUR_TOKEN</code>.</p>"
                    "</body></html>",
                    status_code=401,
                )
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        response = await call_next(request)
        if path == "/dashboard":
            response.set_cookie("aethon_dash", token, httponly=True, samesite="strict")
        return response


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
