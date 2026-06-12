---
id: security
title: Security
sidebar_label: Security
---

# Security

AETHON is **local-first** and ships safe defaults:

- **Loopback binding (fail closed):** WebChat (and the dashboard/webhooks mounted on it) bind to `127.0.0.1` by default. To expose beyond localhost, set `channels.webchat.host: 0.0.0.0` **and** a `dashboard.auth_token` — a non-loopback bind **refuses to start** without the token (override with `--insecure-bind` only behind your own authenticating proxy).
- **Shared auth token (deny by default):** when `dashboard.auth_token` is set, **all** routes on the shared app require the token — every `/api/*` (including `/api/status`), `/dashboard`, the FastAPI docs, and unknown paths (401). Public exceptions: `/`, `/health`, `/dashboard/static/*`, and the self-authenticating `/webhook/*`. Both WebSockets (`/ws/chat`, `/ws/dashboard`) validate the Origin header and the token before accepting the upgrade. Token via `aethon_dash` cookie, `Authorization: Bearer`, or `?token=`. Use `/health` (genuinely public) for uptime probes, not `/api/status`.
- **File-access sandbox:** by default, file tools may read/write anywhere under your home directory **except** a blocklist of system and credential paths (`/etc`, `/usr`, `/bin`, `~/.ssh`, `~/.gnupg`, `~/.aethon/credentials`, …). Set `security.workspace_only: true` to confine file tools strictly to `~/.aethon/workspace`.
- **Blocked commands:** the security hook refuses shell commands containing any `security.blocked_commands` entry (default `rm -rf /`, `sudo`, `mkfs`, plus a built-in danger list).
- **Approval gating:** an optional interrupt-based hook can require approval for the actions in `approval.requires_approval` (default `shell`, `file_write`) — it is **off by default** (`approval.enabled: false`). *(The `security.require_approval` field is reserved and not currently enforced.)*
- **Sender allowlists (deny by default):** `security.allowed_senders.<channel>` restricts who may message each channel. On the messaging bots (`telegram`/`discord`/`slack`/`whatsapp`) an **empty allowlist rejects everyone** — add the allowed sender ids to use the bot.
- **Secret masking:** the dashboard `GET /api/config` dump masks sensitive keys (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) to `***`.
- **Memory guard:** the memory guard hook blocks secrets from being written to long-term memory.
- **Webhook verification (fail closed):** set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming webhooks. With an empty secret on a non-loopback bind the `/webhook/*` routes are not registered at all.
- **Credential isolation:** keep tokens out of the config file by referencing `${ENV_VAR}`s and storing secrets under `~/.aethon/credentials/`.

:::warning Before you expose it
The moment you set `channels.webchat.host: 0.0.0.0`, set a `dashboard.auth_token` too —
otherwise anyone who can reach the port has full dashboard + API access.
:::

For the full security model and threat analysis, see
[`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md)
and [`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) in the repo.
