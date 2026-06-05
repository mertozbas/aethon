# Changelog

All notable changes to AETHON are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **Meridian provider removed.** AETHON no longer ships or defaults to the Meridian
  proxy (which relayed a Claude Max subscription — against Anthropic's terms and a
  real account-suspension risk). The `meridian` provider, its auto-start, the
  `meridian:` config section, and the `strands-meridian` dependency are all gone.

### Changed
- **Default provider is now `openai`** (model `gpt-4o`): set an `api_key` for the
  official OpenAI API, or point `host` at any OpenAI-compatible endpoint (base URL).
  The `openai` SDK is now a **core dependency** so the default works out of the box;
  `anthropic` is available as an extra (`pip install aethon-ai[anthropic]`).
  Existing configs with `provider: meridian` must be switched (`aethon init`).
  `security.workspace_only` now defaults to `false` (file tools work under `$HOME`
  except blocked system/credential paths).
- The CLI no longer prints each reply twice — agents run with `callback_handler=None`,
  so only the channel renders the response (the model's text still comes from the result).
- Tool consent prompts are now bypassed by default (`security.bypass_tool_consent: true`):
  AETHON runs headless (gateway/bots) where an interactive per-tool confirmation would
  hang, and it has its own guardrails (blocked commands + the optional approval hook).
  Set it to `false` to restore strands-tools' per-tool prompts.

### Added
- `aethon init` now also configures messaging bots (Telegram/Discord/Slack tokens) and,
  when using Ollama embeddings, offers to install Ollama (via Homebrew) and pull the
  embedding model so memory works out of the box.

## [0.1.1] - 2026-06-05

### Fixed
- **Model providers:** Bedrock now passes the AWS region via `region_name` (it was
  silently dropped); Gemini sends its token cap via `params.max_output_tokens`
  (`GeminiConfig` has no `max_tokens`); Mistral uses the dedicated `api_key` arg and
  forwards `max_tokens`.
- **Scheduler:** scheduled jobs can now deliver to messaging channels — jobs/`schedule_task`
  accept a `recipient` (chat/channel id) used as the message destination instead of a
  hardcoded `"default"` that failed for Telegram/Discord/Slack/WhatsApp.
- **Security:** `security.workspace_only` is now actually enforced (it was ignored). When
  `true`, file tools are confined to `~/.aethon/workspace`; the default is now `false`
  (file tools may work anywhere under `$HOME` except blocked system/credential paths).
  Localized the remaining Turkish security messages to English.
- **Startup status:** the `Scheduler` line now reports `disabled (requires SOPs)` when SOPs
  are off (the scheduler only starts with SOPs enabled).

### Docs
- README corrected to match runtime reality: team/pipeline orchestration is internal and
  deferred to v2 (not a shipped feature); SOP descriptions appear in listings, not the
  system prompt; `security.require_approval` is reserved (approval gating lives in the
  `approval` section, off by default); non-core providers (OpenAI/Bedrock/Gemini/LiteLLM/
  Mistral) require their own SDK; documented scheduler `recipient`.

## [0.1.0] - 2026-06-05

Initial release of AETHON — a self-hosted, provider-agnostic, multi-channel,
multi-agent personal AI assistant built on the Strands Agents SDK.

### Added

#### Model providers
- **Provider-agnostic model backend.** Any Strands-compatible provider can power
  AETHON; the first-run wizard guides you to whichever one you have.
- **Meridian (Claude Max) as the default provider** via the published
  `strands-meridian` package, so the assistant runs on the owner's Claude Max
  quota with no per-token API key. Defaults to Claude Opus 4.8 (1M context),
  with sampling params omitted for Opus 4.7/4.8 (which reject them).
- **Automatic Meridian daemon management.** When the `meridian` provider is
  selected and Meridian isn't already running, `aethon start` launches it as a
  true background daemon (double-fork, reparented to init, started from a neutral
  working directory so no project context bleeds in). An already-running Meridian
  is reused.
- **Alternative providers** out of the box: Anthropic API key, OpenAI, and Ollama
  (local inference, opt-in extra), plus a no-network `fake`/`echo` model for
  tests, CI, and offline fallback.

#### Channels (all entry points in one package)
- **CLI** chat interface (`prompt_toolkit` + `rich`).
- **Web UI / WebChat** — browser-based chat over FastAPI + WebSocket.
- **Telegram** bot (`aiogram` 3.x).
- **Discord** bot (`discord.py` 2.x).
- **Slack** bot (`slack-bolt`).
- **WhatsApp** bridge (`neonize`, experimental, opt-in extra).

#### Multi-agent system
- **Orchestrator + specialist team:** Coder, Researcher, Analyst, and Planner
  specialists, with team orchestration and a `delegate` tool for agent-to-agent
  delegation.
- **SOPs (Standard Operating Procedures):** a built-in SOP runner with the
  bundled procedures (code-assist, pdd, codebase-summary), enabled by default.
- **Scheduler:** cron-based task scheduling (APScheduler) to run SOPs and tasks
  automatically, enabled by default.
- **Human-in-the-loop** approval hook and a security hook layer (command
  filtering, memory protection).

#### Memory and context
- **Vector memory** — a SQLite-backed embedding store with serialized,
  thread-safe DB access.
- **Dynamic context tools** for managing and updating agent state at runtime.

#### Gateway, dashboard, and telemetry
- **FastAPI gateway** with a message router (auth + queue) and **inbound
  webhook** support.
- **Web dashboard** — a single-page app with a REST API, WebSocket live updates,
  and an event bus (thread-safe emit). Ships fully offline (vendored Google
  Fonts; no CDN calls).
- **Optional shared-token dashboard auth** gating `/api/*`, `/dashboard`, and
  `/ws/dashboard` (cookie / Bearer / query token). Empty token means no auth,
  which is fine for the localhost default; set it before exposing on a network.
- **Telemetry** hooks for observability.
- **`GET /health`** liveness probe (always open, used by the Docker healthcheck);
  `/api/status` reports the real package version.

#### Configuration and CLI
- **`~/.aethon/config.yaml`** configuration (pydantic-validated), with
  configurable WebChat bind host (default loopback) and port (18790).
- **First-run setup wizard:** `aethon init` (provider-agnostic, Meridian
  recommended), `aethon doctor`, and `aethon --version`. `aethon start`
  auto-triggers the wizard when no config exists.

#### Packaging and distribution
- **pip install** from PyPI (`aethon`), with all entry points (CLI + WebChat +
  Telegram/Discord/Slack + memory + SOPs + scheduler) in the core install;
  `ollama`, `whatsapp`, `mcp`, and `all` as optional extras. Dashboard assets
  ship in the wheel and sdist.
- **Docker** image (multi-stage build, non-root user, healthcheck, state volume,
  `EXPOSE 18790`) with headless container defaults and a `docker-compose.yml`
  (default host-Meridian path plus an optional `local` Ollama profile).
- **Continuous integration** (GitHub Actions): test matrix on Python 3.10/3.11/3.12
  with ruff lint and pytest, a build job (wheel + sdist + `twine check`), and a
  Docker build job. End-to-end boot test that spawns the real `aethon start` on
  an ephemeral port and verifies `/health`, the dashboard, the chat UI, and a
  WebSocket round-trip.

#### Documentation and licensing
- English-language README and documentation (architecture, getting started,
  configuration, API reference, product, and security).
- **PolyForm Noncommercial 1.0.0** license (source-available; non-commercial use
  free, commercial use forbidden).

[Unreleased]: https://github.com/mertozbas/aethon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mertozbas/aethon/releases/tag/v0.1.0