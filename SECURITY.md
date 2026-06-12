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
from the machine it runs on and secrets are kept out of the config file. You
bring your own model provider, so no model credentials are required by AETHON
itself — they live in your environment (`${ENV_VAR}` references) or your local
provider.

### Network exposure

- **Loopback by default.** The WebChat/dashboard server binds to
  `127.0.0.1` (`channels.webchat.host`, default `127.0.0.1`; default port
  `18790`), so it is reachable only from the local machine.
- **Exposing on a network is fail-closed.** To listen on other interfaces (for
  example `0.0.0.0`, as in the Docker image), you must change the bind host
  explicitly — and a non-loopback bind **refuses to start** without
  `dashboard.auth_token` (override only behind your own authenticating proxy
  with `--insecure-bind`).
- **Shared-token authentication (deny by default).** `dashboard.auth_token` is
  empty by default (no auth, appropriate for the loopback bind). When set, a
  deny-by-default HTTP middleware gates **every** route on the shared app —
  all `/api/*` endpoints (including `/api/status`), `/dashboard`, the FastAPI
  docs, and unknown paths (401, no route disclosure). The enumerated public
  exceptions are `/` (the chat page; its WebSocket is gated separately),
  `/health` (container/LB probes), `/dashboard/static/*` (SPA assets), and
  `/webhook/*` (self-authenticating via HMAC). Both WebSockets (`/ws/chat`,
  `/ws/dashboard`) validate the Origin header and the token before accepting
  the upgrade (close `1008` otherwise). The token may be supplied via the
  `aethon_dash` cookie, an `Authorization: Bearer <token>` header, or a
  `?token=<token>` query parameter. Health monitors should probe `/health`
  (genuinely public), not `/api/status` (now gated).
- **Webhook verification (fail closed).** When `webhook.secret` is set, incoming
  webhook requests must carry a valid `X-Aethon-Signature` HMAC-SHA256 of the
  raw body; an invalid signature is rejected with `403`. With an empty secret
  on a non-loopback bind the `/webhook/*` routes are not registered at all.
- **Network-channel sender allowlists (deny by default).** For the messaging
  bots (`telegram`/`discord`/`slack`/`whatsapp`), an empty
  `security.allowed_senders.<channel>` rejects every sender; add the allowed
  sender ids to use the bot.

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
- **File permissions.** `config.yaml` is written `0600` and `~/.aethon` is
  `0700`, so a config that carries plaintext keys is never group/world-readable.
  `aethon doctor` reports any path that is readable beyond the owner and nudges
  away from a literally-stored `model.api_key`.
- Do not commit real secrets to `config.yaml`. Keep credentials in the
  environment or under `~/.aethon/credentials/`.

### Tool and command safety

Tool execution is governed by the `security` configuration section:

- **`workspace_only`** (default `false`) restricts file and tool operations to
  the workspace directory (`~/.aethon/workspace`) when enabled. With the default
  (`false`), file tools may operate under `$HOME`, while sensitive system and
  credential paths remain blocked. Set it to `true` to confine all file and tool
  activity to the workspace.
- **`bypass_tool_consent`** (default `true`) runs tools headlessly without a
  per-tool confirmation prompt — appropriate for an unattended assistant. Set it
  to `false` to require interactive consent for each tool invocation.
- **`blocked_commands`** (default `["rm -rf /", "sudo", "mkfs"]`) blocks shell
  commands containing any of the listed substrings. Extend this list to match
  your environment.
- **`require_approval`** (default `["shell", "file_write", "send_message"]`)
  marks action types that require approval before they run.
- **`allowed_senders`** provides a per-channel allowlist of sender identifiers
  for messaging channels.

### Hardening checklist before exposing AETHON

- Set `dashboard.auth_token` (and `webhook.secret` if webhooks are enabled).
- Enable `security.workspace_only` to confine file/tool activity to the
  workspace, and review `blocked_commands`.
- Store all tokens and API keys as `${ENV_VAR}` references, not literals.
- Place AETHON behind a TLS-terminating reverse proxy if it must be reachable
  off-host; the built-in server speaks plain HTTP.

For the full threat model, layered architecture, and security checklist, see
[docs/development/SECURITY.md](docs/development/SECURITY.md).
