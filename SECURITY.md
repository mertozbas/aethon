# Security Policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

Older pre-release versions are not supported. Please upgrade to the latest
0.1.x release before reporting an issue.

## Reporting a vulnerability

Please report security vulnerabilities **privately**. Do not open a public
issue, pull request, or discussion for a suspected vulnerability.

Email **mertozbas@gmail.com** with:

- a description of the issue and its potential impact,
- steps to reproduce (a minimal proof of concept is ideal),
- the AETHON version (`aethon --version`) and your environment.

You can expect an acknowledgement within a few days. Once the report is
confirmed, we will work on a fix and coordinate a disclosure timeline with you.
Please allow a reasonable period for a fix to ship before any public disclosure.

## Security model

AETHON is **local-first**. By default every listening service is reachable only
from the machine it runs on, secrets are kept out of the config file, and tool
actions are constrained to the workspace.

### Network exposure

- **Loopback by default.** The WebChat/dashboard server binds to
  `127.0.0.1` (`channels.webchat.host`, default `127.0.0.1`; default port
  `18790`), so it is reachable only from the local machine. The Meridian proxy
  likewise runs on `127.0.0.1:3456`.
- **Exposing on a network is opt-in.** To listen on other interfaces (for
  example `0.0.0.0`, as in the Docker image), you must change the bind host
  explicitly. **Before exposing the dashboard or WebChat beyond loopback, set
  `dashboard.auth_token`.**
- **Dashboard authentication.** `dashboard.auth_token` is empty by default
  (no auth, which is appropriate for the loopback bind). When set, an HTTP
  middleware gates the `/dashboard` page and all protected
  `/api/*` endpoints (`/api/sessions`, `/api/memory`, `/api/config`,
  `/api/scheduler`, `/api/telemetry`, `/api/sops`, `/api/agents`) as well as
  the `/ws/dashboard` WebSocket. The token may be supplied via the
  `aethon_dash` cookie, an `Authorization: Bearer <token>` header, or a
  `?token=<token>` query parameter; a mismatch returns `401`. The liveness
  probes `/health` and `/api/status` are intentionally left ungated.
- **Webhook verification.** When `webhook.secret` is set, incoming webhook
  requests must carry a valid `X-Aethon-Signature` HMAC-SHA256 of the raw body;
  an invalid signature is rejected with `403`.

### Secrets

- **Environment-based resolution.** Configuration values may reference
  environment variables with the `${ENV_VAR}` syntax. A value of exactly
  `${NAME}` is replaced at load time with the value of that environment
  variable, so tokens and API keys can be kept out of `config.yaml` (for
  example `token: "${TELEGRAM_BOT_TOKEN}"`). An unset variable resolves to an
  empty string.
- **Masking in the dashboard.** The dashboard config view (`GET /api/config`)
  returns the full configuration with sensitive fields masked to `***`. The
  masked field names are `api_key`, `token`, `bot_token`, `app_token`,
  `secret`, and `password`. Empty values are left empty rather than masked.
- Do not commit real secrets to `config.yaml`. Keep credentials in the
  environment or under `~/.aethon/credentials/`.

### Tool and command safety

Tool execution is governed by the `security` configuration section:

- **`workspace_only`** (default `true`) restricts file and tool operations to
  the workspace directory (`~/.aethon/workspace`).
- **`blocked_commands`** (default `["rm -rf /", "sudo", "mkfs"]`) blocks shell
  commands containing any of the listed substrings. Extend this list to match
  your environment.
- **`require_approval`** (default `["shell", "file_write", "send_message"]`)
  marks action types that require approval before they run.
- **`allowed_senders`** provides a per-channel allowlist of sender identifiers
  for messaging channels.

### Hardening checklist before exposing AETHON

- Set `dashboard.auth_token` (and `webhook.secret` if webhooks are enabled).
- Keep `security.workspace_only` enabled and review `blocked_commands`.
- Store all tokens and API keys as `${ENV_VAR}` references, not literals.
- Place AETHON behind a TLS-terminating reverse proxy if it must be reachable
  off-host; the built-in server speaks plain HTTP.

For the full threat model, layered architecture, and security checklist, see
[docs/development/SECURITY.md](docs/development/SECURITY.md).
