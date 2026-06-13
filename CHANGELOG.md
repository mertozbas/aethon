# Changelog

All notable changes to AETHON are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Phase 10 — The Core Loop (C1-C4 stitches; C5-C7 Tiny organs; E2/E3/E4 token economy; E5 memory)

The autonomous core loop's four stitches: a clear unit of work is recognized,
opened as a planned dependency-ordered project, worked to completion by a bounded
executor, and delivered with proof. Plus the token-economy tier that makes
long-horizon work affordable, the Tiny-AI organs, and a more robust long-term
memory that recalls itself.

#### Added — E5 memory: embedding robustness + automatic recall
- **No more silent dimension corruption (E5.1).** Vector memory could mix
  embeddings of different dimensions (e.g. after an embedding-model change) and
  cosine similarity would silently `zip`-truncate to the shorter vector,
  returning a meaningless score with no signal. Now every row records the model
  and dimension that produced it (migration-safe — added to existing DBs; legacy
  rows fall back to the vector's own length); `search` skips rows whose dimension
  differs from the query and warns once per dimension (the condition is
  persistent until re-embedded); and `_cosine_similarity` refuses unequal-length
  vectors outright. Re-embeddable, never silently wrong.
- **Memories that recall themselves (E5.2).** With `memory.auto_recall` on
  (opt-in, default OFF), each turn embeds the incoming message and injects the
  top matching long-term memories as a "## Recalled Memories" prompt layer — so
  relevant memories surface without the agent having to call the memory tool.
  Cache-aware and race-free: the block is threaded into the prompt as an argument
  (not a shared attribute, so concurrent sessions can't cross-inject), lives in
  the volatile suffix, and only recomposes when the recalled set changes (tracked
  per-agent), so an unchanged turn keeps the provider cache warm. Each memory is
  flattened to one line (injection-safe) and framed as untrusted reference data —
  never as instructions — so saved content can't act as a system command.
  Fail-soft: a recall failure leaves the turn untouched. Tunable via
  `recall_top_k`, `recall_min_score`, `recall_max_chars`.
- **Deferred — E5.3 RAG (retrieval over ingested documents).** Retrieval-augmented
  generation over external documents (ingestion, chunking, a separate document
  store, retrieval with citation) is a distinct capability subsystem rather than a
  hardening/recall change, and belongs with the other capability work (web search,
  vision, voice). It is deliberately deferred to a future capability phase, not
  silently skipped — E5 ships the robustness + recall foundation it would build on.

#### Added — E3 repo map + file-summary cache
- **Read it once, remember the map.** When the agent reads a file, a hook caches a
  compact summary beside it — `path → {purpose, top-level symbols, content hash}`
  in `workspace/REPO_MAP.json` — and a "## Repo Map" prompt layer injects that map
  so the agent is oriented without re-reading; it re-reads only for detail or when
  a file may have changed. Extraction is cheap and deterministic (`ast` for
  Python, a first-line fallback otherwise — no model call); the content hash is
  the staleness gate. Cache-safe like E2/C6 (the map file is kept out of the
  volatile prompt fingerprint, so an update doesn't force a per-turn recompose),
  workspace-relative and injection-safe (every rendered field flattened; deleted
  files omitted), bounded to the newest N files, and off by default
  (`repo_map.enabled`).

#### Added — C7 need-driven tool loading
- **Capabilities arrive on demand.** An Operating Rule (shown only when
  `runtime_tools` is enabled) tells the agent that if a task needs a capability no
  current tool provides, it should load or — when permitted — create the tool via
  the existing `manage_tools` (Phase 7) and continue, instead of giving up or
  faking it. New-tool creation stays approval-gated. With C6's diet, the core
  stays small and tools arrive when needed.

#### Added — C6 capability diet
- **Don't carry every tool's schema every turn.** A few tools have huge schemas
  (use_mac is enormous); the diet keeps an always-on core and pulls in the heavy,
  domain-specific tools (use_mac, use_computer, use_github, apple_notes, scraper,
  jsonrpc) only when the session looks like it needs them — by keyword match on
  the message that builds the agent (cheap, no embedding call). Decided PER
  SESSION, not per turn: in the provider APIs the tool list is a separate cached
  array, so changing it every turn would invalidate the prompt/tool cache every
  turn and defeat E1 — the tool set is chosen once and stays stable for the
  agent's lifetime (an eviction + rebuild re-evaluates). Fail-safe (an empty hint
  prunes nothing; only the discoverable set can ever be dropped) and off by
  default (`core_loop.capability_diet`).

#### Added — C5 dynamic specialist creation
- **Raise a soldier on demand.** A new `manage_specialists` tool lets the agent
  define custom specialists (`{name, system_prompt, tools}`) that persist across
  sessions (`workspace/specialists/*.json`) and a generic `ask_specialist(name,
  task)` reaches any specialist — built-in or custom — by name. Bounded by
  default: the feature is opt-in (`core_loop.dynamic_specialists`); a specialist's
  tools must be in a fixed allowlist (resolved at create AND disk-load, so a
  crafted JSON can't smuggle a tool in); powerful tools (shell, python_repl,
  file_write, editor, http_request) need `core_loop.allow_powerful_specialists`;
  the name is slugged (no path traversal); persistence is atomic; and creating a
  specialist is approval-gated. Custom specialists inherit the same security +
  sandbox + hooks as the built-ins.

#### Added — E4 scout specialist
- **Read many, return little.** A new `scout` specialist + `ask_scout` tool: the
  caller points it at sources (files, code, logs) and it reads/searches what it
  needs, returning only a concise conclusion — so the raw dumps stay in the
  scout's context, not the main agent's turn (and its persisted history). The
  development-time "Explore agent" pattern, native. Read-leaning (file_read +
  shell for search + think, no file_write/editor) and inside the same security +
  sandbox + untrusted-marking layer every specialist gets. Isolation is advisory
  (scout follows its brief) with the standard tool-output cap as the structural
  backstop.

#### Added — E2 history compaction
- **Old tool outputs no longer ride along forever.** A long session's dominant
  variable cost is finished tool outputs (a 400-line file read five turns ago)
  re-sent in the model's input every turn. A new `BeforeModelCallEvent` hook
  replaces old, large tool-result *texts* with a compact marker — keeping the
  toolUse/toolResult structure intact, so the model still knows the tool ran but
  doesn't carry its bulk. Cache-aware (so it doesn't fight prompt caching): it
  compacts in batches (only once enough old bulk has piled up) and is
  compact-once-stable (a marked result is never re-touched), so the provider
  message cache is disturbed rarely, not every turn. Invariants: the recent N
  turns (incl. the active one) are never touched, pairing is preserved (text
  rewritten, never removed), thinking blocks stay bit-for-bit; it is in-memory
  only (the disk keeps the full output as an audit trail). Off by default
  (opt-in) via `session.compact_*`.

#### Added — C4 pulse + proof-of-work receipt
- **"Done, here's the proof."** As the executor works a project it sends a
  compact progress pulse to the channel the work came from every N newly-completed
  tasks (silenceable), and on every run-end delivers a structured receipt — each
  task's status with the REAL evidence the ledger captured (never a bare "done",
  never fabricated; a truncated evidence tail is marked, an empty project never
  claims success), plus any dropped tasks and the stop reason. The project's
  parent task remembers its origin channel + recipient (stamped at intake) so the
  receipt goes back to the right place; an agent-initiated project with no origin
  delivers nothing. Delivery is best-effort and bounded (10s timeout), failing
  loud rather than silently dropping. New `core_loop` knobs: `pulse_enabled`,
  `pulse_every_n_tasks`, `receipt_enabled`.

#### Added — C3 execution loop (ambient promoted)
- **Bounded project executor** — `ProjectExecutor` works a planned project to
  completion: pick the most-urgent dependency-satisfied task, drive one agent
  turn, advance when the LEDGER shows it done (never on the agent's prose — done
  requires evidence). Promotes ambient mode: when `core_loop.executor_enabled`
  is on and a project is active, an ambient tick works it via the executor;
  otherwise ambient is unchanged. Off by default. Resume is free — the ledger is
  the durable checkpoint, so a restart picks up where it left off. Runaway
  prevention is the design point and is enforced on every axis: an iteration cap,
  the E0 budget ceiling re-checked between tasks, and a DURABLE per-task attempt
  limit (`executor_attempts` in the ledger) — a task that exhausts it is dropped
  for good, so it can't be retried past its limit across ticks or restarts.

#### Added — C1 intake (chat vs. work)
- **Advisory work intake** — when `core_loop.intake_enabled` is on, a clear unit
  of work is classified, opened as a planned project (reusing the C2 planner
  pipeline), and acknowledged, instead of being answered as a normal chat turn.
  Off by default — chat is untouched. The classifier is a transparent, high-bar
  heuristic: a creation/build verb paired with a project/artifact noun, matched
  as whole words (Turkish-aware), with explicit `intake_work_phrases` /
  `intake_chat_phrases` overrides (chat wins). It is deliberately fail-safe —
  intake off, a chat verdict, or a plan that can't be opened all fall through to
  the untouched normal path, so ordinary chat is never hijacked. A cheap-tier
  model classifier can slot in behind the same interface later.

#### Added — C2 plan → ledger pipeline
- **Task hierarchy + dependency ordering (C2)** — the flat task schema gains four
  optional, migration-safe fields: `parent_id` (the project a task belongs to),
  `depends_on` (ids that must be done first), `priority`
  (critical|high|medium|low), and `due`. `available_tasks(parent_id)` returns the
  open tasks whose dependencies are satisfied, most-urgent-first — the resolver
  the C3 executor will pull from. A `dropped` dependency satisfies the edge (a
  cancelled task can't block the project); a broken/typo'd `depends_on` fails
  safe (the task stays blocked, never runs out of order). `manage_tasks` gains
  the matching params with validation (unknown ref/parent, invalid priority,
  self-dependency, and cycle rejection).
- **Structured plan → ledger (C2)** — `ask_planner` asks the planner specialist
  for structured output (`PlanSchema`: a project + ordered child tasks with
  acceptance criteria, priority, and dependency refs) and writes it into the
  ledger as a dependency-ordered project tree; the plan becomes a visible ledger
  diff (priority + dependencies now show in the prompt snapshot) instead of free
  text. Falls back to a free-text plan when a provider can't force structured
  output. New `core_loop.plan_approval` flag (recorded + surfaced now; the C3
  executor will enforce it).

#### Fixed (C2 adversarial review — round 1)
End-of-stitch review (19 findings → 13 confirmed); each fix ships a regression
test. Highlights: a `dropped` dependency no longer deadlocks dependents;
non-dict / explicit-null entries in a hand-edited `TASKS.json` normalize on read
instead of crashing; `persist_plan` isolates each dependency edge so one failure
can't orphan a half-plan; the planner→ledger wiring can't null an already-active
ledger; unknown-dependency errors are length-bounded; and `ask_planner` moved off
the deprecated structured-output API.

#### Fixed (C1 adversarial review — round 1)
End-of-stitch review (22 findings → 11 confirmed/partial); the two substantive
HIGH issues fixed, each with a regression test. (1) Chat hijacking: the work
heuristic fired on a creation verb alone ("build a stronger relationship"), so it
now requires a verb *and* a project noun. (2) Budget bypass: intake returns
early, so the planner's tokens went unmetered — they are now captured against the
E0 budget. The rest were by-design (one shared single-user ledger) or pre-existing
(specialist timeouts/metering, tracked for a later E0 pass).

#### Fixed (C3 adversarial review — round 1, runaway-focused)
End-of-stitch review (15 findings → 12 confirmed/partial); the runaway root cause
fixed with a regression test. ~7 findings converged on one hole: the per-task
attempt counter was in-memory and per-run, and a "stuck" task was never persisted
as such, so every ambient tick / restart reset the counter and re-attempted it
past its limit. Now the count is a durable ledger field and a task that exhausts
it is dropped — the limit is global across re-invocations and restarts. Also
fixed a concurrency revert (a user-completed task is no longer reset to
in_progress). The Turkish executor prompt (agent-facing) and config-bound guards
were reviewed and left as-is.

#### Fixed (C4 adversarial review — round 1)
End-of-stitch review (20 findings → 11 confirmed/partial); each fix ships a
regression test. The origin fields are now backfilled + flattened on read (a
pre-C4 ledger loads them; a hand-edited newline can't fabricate message structure
in the receipt). The receipt is kept honest: an empty project never reports
"complete", and truncated evidence is explicitly marked so a FAIL at the tail
can't be hidden. Delivery is bounded by a 10s timeout so a hung adapter can't
stall the executor. The pulse-durability-across-resume and send-timeout severities
were downgraded by independent verification (best-effort, opt-in).

### Phase 9B — Robustness, Liveness & Token Economy (H1-H11, E0-E1)

Makes AETHON feel alive, survive always-on use, and measure + cache its token
spend.

### Changed
- **Prompt cache architecture (E1)** — `compose()` now orders layers by
  volatility: a stable prefix (personality, environment, preferences, SOP list,
  Operating Rules, delegation, session) first, then the volatile suffix
  (context, open tasks, handoff, learnings, time) last. Provider prompt caching
  keys on the unchanged prefix → cached-input discount (Anthropic ~90%, OpenAI
  ~50%). The recent-logs layer is dropped from the default prompt (it changed
  every turn and poisoned the cache; opt in with `prompt.include_recent_logs`),
  and `CONTEXT`/`LEARNINGS` injection is capped. A regression test pins the
  stable prefix byte-stable across composes.

### Fixed
- **Disk retention (H7)** — session-reset backups (`cleared/batch_*`) grew
  forever. They (and recordings) are now pruned at boot per a new `retention`
  config: keep the newest N cleared-batches per session and the newest N
  recordings, with an optional recording age cap. `aethon doctor` shows a disk
  usage report.
- **Config safety (H8)** — a typo'd or removed config key used to be silently
  ignored. `AethonConfig.load` now warns and lists unknown keys (walking nested
  sections, leaving free-form dicts like `scheduler.jobs` alone), and
  `aethon doctor` reports them. `aethon init` backs up an existing config to
  `config.yaml.bak-<timestamp>` before overwriting. New `config_version` field
  for future migrations.
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
- **Token measurement + budget ceiling (E0)** — every turn's token usage is now
  measured (diffed from the agent's accumulated usage) and costed via a
  config-overridable pricing table (`budget.pricing`; built-in rates as of
  2026-06). With `budget.daily_usd` set, turns are warned near the ceiling and
  blocked once it's breached (which also stops ambient/scheduler turns, since
  they run through the same path) with a localized message. The real antidote to
  the "an API will burn hundreds of dollars" fear. `TokenMeter.summary()` exposes
  the data (a dashboard cost panel can consume it).
- **`aethon backup` + run-at-boot service (H10/H11)** — `aethon backup` archives
  `~/.aethon` to a `.tar.gz` (SQLite copied live-safe, `logs/` skipped);
  `aethon service install` writes a launchd agent (macOS) or systemd user unit
  (Linux) that keeps the gateway running and restarts on failure, logging to
  `~/.aethon/logs/`. New `website/docs/operations/backup-and-service.md`.
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

### Fixed (Phase 9B adversarial review — round 1)

End-of-phase review across independent dimensions; each finding independently
refuted before fixing, each fix shipped with a regression test.
- **Agent-cache thread safety (H1, HIGH)** — the per-session `asyncio.Lock` only
  serialized same-session turns; different sessions mutated the shared, unlocked
  `self.agents` LRU from executor threads at once, overflowing its bound or
  evicting an in-use agent. The check-then-act and every eviction site now run
  under a `threading.RLock`.
- **Scheduler serialization (H4, HIGH)** — config-defined cron SOPs ran through
  the shared `scheduler:cron` agent while bypassing the H1 lock, so two jobs
  firing in the same window corrupted its session file. An `asyncio.Lock` now
  serializes all scheduled execution.
- **SOP turn metering (E0, HIGH)** — `_capture_usage` ran only on normal turns,
  so SOP turns went unmetered and their tokens inflated the next turn's diff and
  escaped the budget ceiling. SOP turns are now metered off the agent's own
  metrics.
- **Reset-backup data loss (H7, HIGH)** — session-reset backups were named
  `batch_<count>`; after retention pruned the lowest batches the count collided
  with a survivor, `mkdir` raised, and the fallback **deleted** the history
  instead of backing it up. Backups are now numbered max+1 (collision-proof) and
  the delete fallback is fail-loud.
- **Lone-bot shutdown (H3, MEDIUM)** — a single network bot's transient clean
  return ended its supervisor and tore the gateway down. A `blocking` adapter
  flag now distinguishes a long-running channel (restarted on an unexpected
  return) from a fire-and-return one like WhatsApp (done on return).
- **Fail-loud + docs (LOW)** — `_setup_file_logging` no longer swallows setup
  errors (warns on stderr); the `prompt.py` docstring and `CAPABILITIES.md`/
  README now describe the post-E1 layer order and `include_recent_logs` default.

### Phase 9A Sprint 1 — Network security (S1-S5)

Closes the remote-RCE-grade network findings of the seven-lens gap analysis:
deny by default on every network surface, fail closed at startup.

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
- **Security model truth pass (S10)** — the security-model doc rewritten to
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
from *trusting* the agent's word to *verifying* it.

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