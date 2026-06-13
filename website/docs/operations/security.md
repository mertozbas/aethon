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
- **Approval gating:** an optional interrupt-based hook can require approval for the actions in `approval.requires_approval` (default `shell`, `file_write`, `manage_tools`, `manage_specialists`) — it is **off by default** (`approval.enabled: false`). *(The `security.require_approval` field is reserved and not currently enforced.)*
- **Sender allowlists (deny by default):** `security.allowed_senders.<channel>` restricts who may message each channel. On the messaging bots (`telegram`/`discord`/`slack`/`whatsapp`) an **empty allowlist rejects everyone** — add the allowed sender ids to use the bot.
- **Execution sandbox (opt-in):** set `security.sandbox: docker` to run the `shell` tool inside a disposable per-session container with resource caps (`sandbox_memory`, `sandbox_cpus`, `sandbox_pids_limit`), no host network by default (`sandbox_network: none`), and a read-only rootfs. It **refuses to start** if `docker` is selected but unavailable (fail closed). The default `none` runs shell on the host under the blocked-commands list. *(File tools stay host-side in this version.)*
- **Untrusted-content marking (on by default):** with `security.mark_untrusted_content: true`, results from external-content tools (`scraper`, `http_request`, `jsonrpc`, `use_github`) and inbound webhook payloads are wrapped in `[UNTRUSTED EXTERNAL CONTENT]` markers so the model treats them as data, not instructions. This is **honest marking, not an injection detector** — set it `false` to disable.
- **Secret masking:** the dashboard `GET /api/config` dump masks sensitive keys (`api_key`, `token`, `bot_token`, `app_token`, `secret`, `password`) to `***`.
- **Memory guard:** the memory guard hook blocks secrets from being written to long-term memory.
- **Webhook verification (fail closed):** set `webhook.secret` to require an HMAC-SHA256 `X-Aethon-Signature` on incoming webhooks. With an empty secret on a non-loopback bind the `/webhook/*` routes are not registered at all.
- **Credential isolation:** keep tokens out of the config file by referencing `${ENV_VAR}`s and storing secrets under `~/.aethon/credentials/`.

:::warning Before you expose it
The moment you set `channels.webchat.host: 0.0.0.0`, set a `dashboard.auth_token` too —
otherwise anyone who can reach the port has full dashboard + API access.
:::

For the full security model and threat analysis, see
[`SECURITY.md`](https://github.com/mertozbas/aethon/blob/main/SECURITY.md) in the repo.
