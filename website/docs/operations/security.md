---
id: security
title: Security
sidebar_label: Security
---

# Security

AETHON is **local-first** and ships safe defaults:

- **Loopback binding:** WebChat (and the dashboard/webhooks mounted on it) bind to `127.0.0.1` by default. To expose beyond localhost, set `channels.webchat.host: 0.0.0.0` **and** a `dashboard.auth_token`.
- **Dashboard auth token:** when `dashboard.auth_token` is set, `/dashboard`, the protected `/api/*` prefixes, and `/ws/dashboard` require the token (via `aethon_dash` cookie, `Authorization: Bearer`, or `?token=`). `/api/status` and `/health` stay open for probes.
- **File-access sandbox:** by default, file tools may read/write anywhere under your home directory **except** a blocklist of system and credential paths (`/etc`, `/usr`, `/bin`, `~/.ssh`, `~/.gnupg`, `~/.aethon/credentials`, …). Set `security.workspace_only: true` to confine file tools strictly to `~/.aethon/workspace`.
- **Blocked commands:** the security hook refuses shell commands containing any `security.blocked_commands` entry (default `rm -rf /`, `sudo`, `mkfs`, plus a built-in danger list).
- **Approval gating:** an optional interrupt-based hook can require approval for the actions in `approval.requires_approval` (default `shell`, `file_write`) — it is **off by default** (`approval.enabled: false`). *(The `security.require_approval` field is reserved and not currently enforced.)*
- **Sender allowlists:** `security.allowed_senders` can restrict who may message each channel.
- **Secret masking:** the dashboard `GET /api/config` dump masks sensitive keys (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) to `***`.
- **Memory guard:** the memory guard hook blocks secrets from being written to long-term memory.
- **Webhook verification:** set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming webhooks.
- **Credential isolation:** keep tokens out of the config file by referencing `${ENV_VAR}`s and storing secrets under `~/.aethon/credentials/`.

:::warning Before you expose it
The moment you set `channels.webchat.host: 0.0.0.0`, set a `dashboard.auth_token` too —
otherwise anyone who can reach the port has full dashboard + API access.
:::

For the full security model and threat analysis, see
[`docs/development/SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/docs/development/SECURITY.md)
and [`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) in the repo.
