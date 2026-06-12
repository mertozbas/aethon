# Changelog

All notable changes to AETHON are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 9B Sprint 1 — Liveness

Makes AETHON feel alive and stop failing silently. Design doc:
`docs/development/PHASE-9B-ROBUSTNESS.md`.

### Fixed
- **Root file logging (H9)** — the rotating `aethon.log` handler now attaches to
  the root logger, so third-party errors (strands, uvicorn, aiogram, discord,
  slack) reach the file instead of only `aethon.*`. New `logging` config:
  `level` (AETHON loggers, default INFO) and `third_party_level` (library floor,
  default WARNING). Model errors already log with `exc_info=True` (H2/H3).
- **Single-instance guard (H6)** — a second `aethon start` no longer silently
  fights the first over `~/.aethon` (double writes, Telegram getUpdates
  conflict): an exclusive `flock` on `~/.aethon/aethon.pid` makes it exit with
  "already running (pid N)". No-op where `fcntl` is unavailable.
- **Adapter supervision (H3)** — one channel crashing used to tear down the
  whole gateway, and the cause was never logged (`asyncio.wait` returned and
  `shutdown()` ran unconditionally, the `done` set ignored). Each adapter now
  runs under a supervisor: a crash is logged with traceback and restarted with
  exponential backoff (capped), and after the retry budget the channel is
  degraded — the rest of AETHON keeps running. The gateway shuts down only on a
  signal, the interactive CLI exiting, or every channel ending.
- **Per-session turn serialization (H1)** — two messages to the same session
  could race the same cached Agent across executor threads and corrupt its
  session file. `runtime.process` now holds a per-`session_id` `asyncio.Lock`
  for the whole turn, so same-session turns serialize while different sessions
  stay parallel. Supersedes (and replaces) the WebChat-only turn lock added in
  Phase 9A.

### Added
- **Scheduler persistence + one-shot reminders + free-text (H4)** — runtime
  `schedule_task` jobs no longer vanish on restart: they persist to
  `workspace/SCHEDULE.json` and reload at boot, recovering one-shots missed
  while AETHON was down. `schedule_task` now also takes `run_at` (an ISO
  timestamp → a one-shot DateTrigger, so "remind me tomorrow at 15:30" works)
  and a free-text `prompt` payload that runs through the agent — not only named
  SOPs. Config-defined jobs stay declarative (not persisted).
- **Progress indicators (H5)** — long turns no longer look identical to a crash:
  Telegram shows `typing…` (refreshed every ~4s) and Discord shows its typing
  indicator while a turn runs, stopping on completion. Wired via a
  `typing_context` the base no-ops and each adapter overrides.
- **User-facing error replies (H2)** — a model/runtime failure no longer leaves
  a bot silent: every channel now sends a short, localized last-resort reply
  (classifies auth/quota/timeout/model errors, falls back to naming the
  exception class) pointing at `aethon doctor`. Language follows the user's
  message (Turkish if it contains Turkish characters). Wired once in
  `ChannelAdapter.on_message` (covers Telegram/Discord/Slack/WhatsApp) and in
  the CLI/WebChat direct paths.

### Phase 9A Sprint 1 — Network security (S1-S5)

Closes the remote-RCE-grade network findings of the seven-lens gap analysis:
deny by default on every network surface, fail closed at startup. Design doc:
`docs/development/PHASE-9A-SECURITY.md`.

### Added
- **Execution sandbox foundation (S7, staged)** — new `security.sandbox`:
  `none` (default, host execution under the command blocklist) or `docker`. In
  `docker` mode the `shell` tool runs in a disposable per-session container
  (workspace mounted at `/workspace`, no host home, no host network by default,
  `--memory`/`--cpus`/`--pids-limit` caps) instead of on the host — so bypassing
  the substring blocklist no longer matters, the blast radius is a throwaway
  container. Refuses to start if `docker` is selected but unavailable (fail
  closed); containers are torn down on shutdown. File tools stay host-side in
  this version (documented).
- **Untrusted-content marking (S9)** — results from external-content tools
  (`scraper`, `http_request`, `jsonrpc`, `use_github`) and webhook payloads are
  wrapped in `[UNTRUSTED EXTERNAL CONTENT]` delimiters via an advisory
  `AfterToolCallEvent` hook (registered to run after truncation), and the
  Operating Rules layer gains a rule that tool results are data, never
  instructions. Honest marking that reduces instruction-following on injected
  content — explicitly **not** an injection detector. Gate:
  `security.mark_untrusted_content` (on by default).
- **Secrets hygiene (S8)** — `AethonConfig.write` now `chmod 0600`s the config
  file and `0700`s `~/.aethon` (the documented "0600 credential isolation" was
  never implemented). `aethon start` re-restricts `~/.aethon`; `aethon doctor`
  reports group/world-readable config/credential paths and a literally-stored
  `model.api_key`. The wizard nudges toward a `${ENV_VAR}` reference when a key
  is typed in.
- **Answerable approval (S6)** — the interrupt-based approval hook is no longer
  half-wired: a gated tool (`shell`/`file_write`/`manage_tools` by default) now
  pauses the turn and asks for a yes/no answer on the originating channel — CLI
  (inline `[e/h]`), WebChat (a ✅/❌ card over the socket), Telegram (an inline
  keyboard, presser re-authorized against the allowlist). The decision is
  enforced (deny cancels the tool — the missing half that made enabling it
  wedge the session, finding F6). Channels that can't answer **fail closed**
  (deny with a clear message), as does a timeout (`approval.timeout_seconds`,
  default 120s). `approval.enabled` stays `false` by default — it is now safe
  to turn on.
- **`/ws/chat` authentication (S1)** — the chat WebSocket requires the shared
  `dashboard.auth_token` when one is set, rejected before `accept()` (close
  1008). Token sources: `?token=`, `Authorization: Bearer`, `aethon_dash`
  cookie. The chat page prompts for the token on first connect
  (sessionStorage) and now builds a proto-aware URL (`wss:` behind TLS).
- **WebSocket Origin validation (S2)** — `/ws/chat` and `/ws/dashboard`
  validate the browser `Origin` header before the upgrade (WebSockets bypass
  same-origin policy, so any web page could otherwise drive a loopback bind).
  Default: same-host origins; extend via `channels.webchat.allowed_origins`.
  Mismatch (including `Origin: null`) closes `1008` and logs the origin;
  clients without an Origin header pass — the token is their gate.
- **`--insecure-bind` flag (S4)** — `aethon start` refuses a non-loopback
  `channels.webchat.host` when `dashboard.auth_token` is empty (gateway raises
  the same refusal as defense-in-depth). The flag opts out, intended only for
  deployments behind their own authenticating reverse proxy. Docker:
  `AETHON_DASHBOARD_TOKEN` is now effectively required (the container binds
  `0.0.0.0`); README documents a reverse-proxy/TLS recipe.

### Changed
- **SECURITY.md truth pass (S10)** — `docs/development/SECURITY.md` rewritten to
  match the code: the phantom "Layer 5: Content Filtering" (a hook that never
  existed) is removed, the real layers (S1-S9 + Phase 8 hooks) are documented,
  and the **explicit non-goals** are stated plainly (no injection detection;
  `sandbox: none` residual risk; file tools not yet sandboxed; single-user trust
  model; the blocklist is a tripwire, not a boundary). Advertising a protection
  that does not exist is itself a risk — the doc no longer claims more than the
  code does.
- **BREAKING: default-deny sender authorization on network channels (S5)** —
  an empty `security.allowed_senders.<channel>` now means **reject all** for
  `telegram`/`discord`/`slack`/`whatsapp` (previously: allow everyone).
  Existing bot setups must add their sender ids, e.g.
  `security.allowed_senders.telegram: ["123456"]` — the rejection reply and a
  startup ERROR both name the exact key. `cli`/`webchat` keep the local
  exception (WebChat is token-gated by S1 instead); `webhook:*`
  pseudo-channels are unaffected (HMAC-gated by S3). Rejected senders now get
  a short fixed reply instead of a silent drop. The wizard gains a WhatsApp
  step (enable + default chat + allowlist), completing channel parity.
- **HTTP auth middleware inverted to deny-by-default (S1)** — with a token set,
  ALL routes on the shared app are protected (including `/api/status`, the
  FastAPI `/docs`/`/openapi.json`, and unknown paths → 401); the old
  `_protected` prefix allowlist is gone. Enumerated public exceptions: `/`,
  `/health`, `/dashboard/static/*`, and the self-authenticating `/webhook/*`.
  The middleware now installs at app construction, so it also applies when the
  dashboard is disabled.
- **Startup output prints the real bind host (S4)** — `aethon start` and the
  gateway no longer print hardcoded `http://127.0.0.1:…` URLs when bound
  elsewhere.
- **Webhooks fail closed (S3)** — an empty `webhook.secret` on a non-loopback
  bind no longer registers the `/webhook/*` routes (startup ERROR names the
  key); loopback + empty secret keeps working for local dev, with a WARN. The
  wizard now offers to generate a webhook secret; Docker passes it via
  `AETHON_WEBHOOK_SECRET`.

### Phase 8 — Reliability Hardening (R1-R18)

Derived from the hermes-strands autonomous-development audit: moves AETHON
from *trusting* the agent's word to *verifying* it. Design doc:
`docs/development/PHASE-8-RELIABILITY.md`.

### Fixed
- **`update_context` double-path bug (R1)** — every write raised
  `NotADirectoryError` (`CONTEXT.md/CONTEXT.md`); the agent's only durable
  scratchpad never persisted. Regression test pins the write path to the
  exact file the prompt composer reads.
- **Recipient resolver ported to Discord/Slack/WhatsApp (R2)** — the
  `int('default')` proactive-send crash class fixed for Telegram was still
  live in the other three channels. New config: `discord.channel_id`,
  `slack.channel`, `whatsapp.chat`.
- **`send_message` no longer lies (R3)** — recipient validated before
  dispatch; worker-thread sends run on the gateway loop and report the real
  outcome; in-loop sends say "queued", never "sent".
- **Editor `.bak` sidecar leak (R4)** — `EDITOR_DISABLE_BACKUP` defaulted on;
  `*.bak` gitignored; stray workspace sidecars removed.
- **Silent failures surfaced (R5)** — tool error results log input + error
  text; 14 blanket import guards split (ImportError silent, real bugs
  logged); router/scheduler silent excepts now log.
- **Specialists bounded (R8)** — process-cached specialist agents get a
  `SummarizingConversationManager` (no more unbounded history → overflow).

### Added
- **Verification backstop (R6, R7)** — `PostEditVerifyHookProvider` runs the
  configured `reliability.verify_cmd` (or auto-detected `ruff check`) on
  edited files and appends `[Verify] PASS/FAIL` to the tool result;
  `CompletionGateHookProvider` flags success claims that carry no PASS
  evidence. Advisory by default; `reliability.strict` hardens both.
- **Task Ledger (R9)** — durable `TASKS.json` working state via the new
  `manage_tasks` tool (completion requires evidence) + an `## Open Tasks`
  prompt layer that survives resets and restarts.
- **Per-turn prompt refresh (R10)** — CONTEXT.md / ledger / handoff updates
  now surface mid-session (`prompt.refresh_per_turn`).
- **Reset checkpoints (R11)** — session resets write a compact orientation
  checkpoint to `HANDOFF.md`, read back as a prompt layer.
- **Ledger-bound ambient mode (R12)** — idle cycles work the recorded
  backlog; the completion signal also requires an empty ledger.
- **Operating Rules prompt layer (R13)** — Definition of Done, no
  anglicization, surface-don't-hide, commit hygiene, ledger discipline —
  shipped in code, not workspace prose.
- **Enforcement hooks (R14-R17)** — anglicization guard (TR→EN edit pause),
  commit-hygiene blocks (`git add .`/`-A`/`commit -a`, `*.bak`),
  self-describing input validation for malformed tool calls, and a
  repeated-tool-failure surfacer (3 failures/10 min → loud notice).
- **`reliability` config section** — `strict`, `post_edit_verify`,
  `verify_cmd`, `verify_timeout`, `completion_gate`, `anglicization_guard`.

### Fixed (post-implementation adversarial review, 2 full rounds — 40 findings: 26 fixed, 14 verified-already-fixed)
- Scheduled SOPs no longer block the gateway loop (executor offload); a
  timed-out send_message is cancelled instead of delivering late after
  reporting failure.
- TASKS.json mutations are locked (concurrent tool calls lost tasks /
  duplicated ids); corrupt ledgers are quarantined, never clobbered.
- Ledger/handoff text is whitespace-flattened before reaching the system
  prompt (persistent prompt-injection vector closed); HANDOFF rotation is
  line-anchored; reset checkpoints sort message files numerically.
- Per-turn prompt refresh is mtime-gated — unchanged sources leave the
  prompt byte-identical, preserving provider prompt caching.
- CompletionGate implements the designed ledger-evidence branch (flags
  unevidenced in-progress tasks by name) and works from the ledger alone.
- Shell security checks cover list/dict-form commands (previously bypassed
  ALL checks incl. blocked_commands); R15 git-hygiene checks are
  quote-aware token analysis (no more -m message false positives).
- Discord explicit recipients resolve or fail loudly (no silent redirect
  to the default); id coercion is exception-safe; WhatsApp reactive
  failures are owned and logged; repeated-tool-failure notices also
  escalate out-of-band to the session's channel.
- Ambient mode can no longer spin forever on a blocked backlog; the setup
  wizard collects Discord/Slack destinations + allowlists (Telegram parity);
  reliability.input_validator flag added; degraded hooks aggregate into a
  startup health record.

### Changed
- Hook housekeeping (R18) — SOP prompt layer reads `SOPRunner.list_sops()`;
  ApprovalHook construction guarded; reliability-hook startup failures
  escalate to ERROR. Repo made fully ruff-clean.

## [0.2.0] - 2026-06-08

### Added
- **Capability tools** — `scraper` (BeautifulSoup), `use_github` (GitHub GraphQL),
  `jsonrpc` (HTTP/WebSocket), `notify` (native notifications), `manage_messages`
  (turn-aware self-introspection); grouped under a new `capabilities` config block.
- **macOS native** — `use_mac` (Calendar/Reminders/Mail/Contacts/Safari/Finder/
  Shortcuts/Messages/Music/Keychain) and `apple_notes`, Darwin-gated; Messages and
  Keychain off by default. New `macos` config + `[macos]` extra.
- **Code intelligence** — `lsp` tool + `LSPDiagnosticsHookProvider`; `lsp` config +
  `[lsp]` extra (pyright).
- **Dynamic tool loading** — `manage_tools` with a subprocess sandbox and 3-layer
  gating; `runtime_tools` config.
- **Computer control** — `use_computer` (opt-in, approval-gated); `[computer]` extra.
- **Ambient / autonomous mode** — opt-in background loop; `ambient` config.
- **Session recording & replay** — recorder hook + `LoadedSession` + 5 dashboard API
  endpoints + a Recordings dashboard tab; `session_recorder` config + `paths.recordings`.
- **MCP server** — `aethon mcp` exposes the toolset to MCP clients over stdio;
  `runtime.get_tools_schemas()`.
- **System-prompt awareness** — environment / learnings / recent-logs / shell-history /
  self-awareness layers + the `record_learning` tool; `prompt` config + file logging.
- **Dashboard** — a **Features** panel (live capability status) and an identity-correct
  **Live Company** (pixel agents reflect real tool/model activity).
- **Bundled `codex-proxy`** (source only) for the ChatGPT-Pro-via-OpenAI-compatible
  backend; new `launcher-macos` extra (`aethon-menubar`).

### Changed
- Oversized tool output is capped (`performance.max_tool_output_chars`, default 12000)
  so a single huge command can't overflow the model context.
- The runtime forces strands-tools into non-interactive mode and quiets benign provider
  log noise, so tool output no longer corrupts the CLI.

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