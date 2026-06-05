# Contributing to AETHON

Thanks for your interest in contributing to AETHON — a personal AI assistant
built on the Strands Agents SDK.

AETHON is licensed under
[PolyForm Noncommercial 1.0.0](LICENSE). It is source-available, not OSI
open-source: you may use, modify, and redistribute it for **noncommercial**
purposes. Contributions are accepted under the same terms — by submitting a pull
request you agree your contribution is licensed under PolyForm Noncommercial 1.0.0.

## Table of contents

- [Development environment setup](#development-environment-setup)
- [Running the test suite](#running-the-test-suite)
- [Linting](#linting)
- [Project layout](#project-layout)
- [How to add a provider](#how-to-add-a-provider)
- [How to add a channel](#how-to-add-a-channel)
- [How to add an SOP](#how-to-add-an-sop)
- [How to add a tool](#how-to-add-a-tool)
- [Commit and pull request conventions](#commit-and-pull-request-conventions)
- [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)

## Development environment setup

AETHON targets **Python 3.10, 3.11, or 3.12** (`requires-python = ">=3.10"`). CI
runs the full matrix on all three, so develop against any of them.

```bash
git clone https://github.com/mertozbas/aethon.git
cd aethon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`pip install -e ".[dev]"` installs AETHON in editable mode plus the test
tooling (`pytest>=8`, `pytest-asyncio>=0.23`, `httpx>=0.27`). The core install
already ships every entry point — CLI, WebChat, the dashboard, the
Telegram/Discord/Slack bots, memory, SOPs, and the scheduler — so you don't need
any extras for most work.

Optional feature extras, only when you're working on that feature:

| Extra | Adds | For |
|-------|------|-----|
| `ollama` | `ollama>=0.3.0` | local-inference provider |
| `whatsapp` | `neonize>=0.3.0` (experimental) | WhatsApp channel |
| `mcp` | `mcp>=1.0.0` | MCP integration |
| `all` | `aethon[ollama,whatsapp,mcp]` | all of the above |

Install them alongside dev, e.g. `pip install -e ".[dev,ollama]"`.

The default model provider is **OpenAI** (`gpt-4o`). To exercise a real provider
locally, configure one in `~/.aethon/config.yaml` (or run `aethon init`):

```yaml
model:
  provider: openai
  model_id: gpt-4o
  api_key: ${OPENAI_API_KEY}   # official OpenAI API
  # host: http://localhost:11434/v1  # or point at any OpenAI-compatible base URL
# Local, no API key:
# model:
#   provider: ollama
#   model_id: llama3.1
```

`openai` works against the official OpenAI API (set `api_key`) or any
OpenAI-compatible endpoint (set `host` to its base URL — e.g. vLLM, LM Studio,
LocalAI). You do **not** need any network model for the test suite — tests use the
offline `fake`/`echo` provider.

## Running the test suite

Tests live under `tests/` and are configured in `[tool.pytest.ini_options]` in
`pyproject.toml`.

```bash
pytest                  # full suite (this is what CI runs, as `pytest -q`)
pytest -m "not e2e"     # skip end-to-end boot tests
pytest tests/path/to/test_file.py        # a single file
pytest -k some_keyword                    # tests matching a keyword
```

Two markers are defined:

- **`e2e`** — end-to-end boot tests that spawn a subprocess and bind a socket.
  They're slower and need a free port; deselect them with `pytest -m "not e2e"`
  for a fast inner loop.
- **`ollama`** — tests that require a running Ollama instance. Skip with
  `pytest -m "not ollama"` if you don't have Ollama running.

Async tests use `pytest-asyncio`. Prefer testing against real data and real code
paths over mocks.

## Linting

CI runs an **error-level** Ruff gate. Match it exactly before pushing:

```bash
ruff check --select E9,F63,F7,F82 aethon
```

These rules catch syntax errors (`E9`), invalid literal comparisons and `f`-string
issues (`F63`, `F7`), and undefined names (`F82`) — i.e. things that would break
at import/runtime. If `ruff` isn't on your PATH, install it with `pip install ruff`
(CI installs it on the fly). Keep this check clean; a failure here fails the build.

## Project layout

```
aethon/                  # the package
  __main__.py            # click CLI: init / doctor / start (+ --version)
  config.py              # Pydantic config models + YAML loader (AethonConfig)
  setup_wizard.py        # interactive `aethon init` wizard (provider menu, bots, embeddings)
  agent/
    model_factory.py     # create_model() — provider dispatch
    runtime.py           # AethonRuntime: assembles the main agent + its tools
    specialists.py       # SPECIALIST_CONFIGS (coder/researcher/analyst/planner)
    teams.py             # multi-agent swarm + pipeline orchestration
    prompt.py            # SystemPromptComposer (SOUL/TOOLS/CONTEXT layering)
    fake_model.py        # offline EchoModel for tests/CI
    hooks/               # approval / telemetry / memory-guard hooks
  channels/
    base.py              # ChannelAdapter ABC + Inbound/Outbound message types
    cli.py, webchat.py, telegram.py, discord_adapter.py,
    slack_adapter.py, whatsapp.py
  gateway/
    server.py            # AethonGateway: starts enabled channels, mounts dashboard/webhooks
    router.py            # routes InboundMessage -> runtime -> response
    webhooks.py          # /webhook/trigger and /webhook/{channel}
  tools/                 # @tool functions: delegate, memory_tool, context_tool,
                         # messaging, scheduler, mcp_integration
  memory/vector.py       # VectorMemory: SQLite + embeddings + cosine search
  sops/runner.py         # SOPRunner: loads + executes SOPs
  ui/                    # dashboard.py, event_bus.py, log_handler.py, static/ (SPA)
docs/
  README.md              # documentation index
  product/               # PRODUCT, GETTING-STARTED, CONFIGURATION, API-REFERENCE, ARCHITECTURE
  development/           # PHASE-* design docs, ROADMAP.md, SECURITY.md (threat model)
  checklists/            # per-phase completion checklists
  references/            # strands-agents-reference.md
docker/                  # config.docker.yaml (seeded container config)
tests/                   # pytest suite
Dockerfile, docker-compose.yml, pyproject.toml, README.md, LICENSE
```

Configuration is the spine of the system: every feature is gated by a section in
`aethon/config.py` and loaded from `~/.aethon/config.yaml`. When you add a feature,
add its config model there. See `docs/product/CONFIGURATION.md` for the full
reference.

## How to add a provider

Model providers are dispatched in `aethon/agent/model_factory.py`.

1. In `create_model(config)`, add an `elif provider == "<name>":` branch that
   constructs and returns a Strands `Model` from the `ModelConfig` fields
   (`model_id`, `temperature`, `top_p`, `top_k`, `max_tokens`, `host`, `api_key`,
   `region`, `extra`). Follow the existing branches (openai, anthropic, ollama,
   bedrock, gemini, litellm, mistral) as templates, and add your name
   to the "Supported:" message in the final `else`.
2. Add a matching branch to `check_model_availability(config)` in the same file so
   `aethon doctor` and `aethon start` can report whether the provider is reachable.
3. If the provider needs new config knobs, add fields to `ModelConfig` (or a new
   section model) in `aethon/config.py`.
4. If it requires a heavy/optional dependency, add an extra in
   `[project.optional-dependencies]` in `pyproject.toml` and import it lazily
   inside the branch (so the base install doesn't pull it in).
5. Wire it into the `aethon init` wizard provider menu in `aethon/setup_wizard.py`
   if it should be offered interactively.
6. Add tests; the offline `fake`/`echo` provider is the model for a backend-free,
   CI-safe test.

## How to add a channel

Channels are adapters under `aethon/channels/`, all subclassing
`ChannelAdapter` (`aethon/channels/base.py`).

1. Create `aethon/channels/<name>.py` with a class subclassing `ChannelAdapter`
   and implementing the abstract methods `start()`, `stop()`, and `send()`. Use
   the inherited `on_message()` to forward an `InboundMessage` to the router and
   send back the response (see `telegram.py` / `discord_adapter.py` for the
   inbound-to-router-to-outbound pattern).
2. Add a config model (e.g. `class FooChannelConfig`) with at least `enabled: bool`
   (plus any tokens) to `aethon/config.py`, and register it as a field on
   `ChannelsConfig`. Raise `ValueError` from `__init__` if a required token is
   missing.
3. Wire startup into `AethonGateway.start()` in `aethon/gateway/server.py`: gate it
   behind `self.config.channels.<name>.enabled`, instantiate the adapter into
   `self.adapters["<name>"]`, and append its `start()` coroutine. Wrap optional or
   library-dependent channels in try/except so a missing lib or token logs a
   warning instead of crashing the gateway.
4. If it needs an optional dependency, add an extra in `pyproject.toml` and import
   the library lazily inside the adapter.
5. Add the channel to the startup banner's channel list (`_print_channels` in
   `aethon/__main__.py`) and to the `send_message` tool's channel set in
   `aethon/tools/messaging.py` if outbound sends should be supported.
6. Tokens belong in the environment, referenced from YAML as `${VAR_NAME}`
   (resolved by `AethonConfig._resolve_env_vars`); never commit secrets.

## How to add an SOP

SOPs are markdown playbooks the agent runs when a message starts with `/<name>`.
Built-ins (`code-assist`, `pdd`, `codebase-summary`) come from the
`strands-agents-sops` package; custom SOPs live in the workspace.

For a **custom SOP** (the common case — no code change needed):

1. Create `~/.aethon/workspace/sops/<name>.sop.md` (the workspace dir is
   `config.paths.workspace`; the runtime registers `<workspace>/sops`).
2. The SOP name is the filename with `.sop.md` stripped, invoked as `/<name>`.
   The loader uses `glob("*.sop.md")`.
3. Add a `## Overview` section — its first ~200 characters become the description
   shown in listings and in the system prompt's "Available SOP Commands".
4. Avoid reusing a built-in name; a same-named custom SOP overwrites the built-in
   in the runner.

To change SOP loading/execution behavior or ship a new built-in, work in
`aethon/sops/runner.py` (`SOPRunner`). The SOP subsystem is gated by
`config.sops.enabled` and built-ins by `config.sops.builtin_sops_enabled`.

## How to add a tool

Tools are Strands `@tool` functions assembled onto the main agent in
`AethonRuntime._get_tools()` (`aethon/agent/runtime.py`). The always-present base
set is `file_read, file_write, editor, shell, think, current_time`; everything
else is added conditionally.

1. Create (or extend) a module in `aethon/tools/` and define your function with the
   Strands `@tool` decorator. Write a clear docstring and typed signature — the
   model reads these to decide when and how to call the tool.
2. If the tool needs runtime state (memory, the gateway, a factory), follow the
   existing pattern of a module-global set by a `set_*()` function wired up in
   `AethonRuntime.__init__` (see `delegate.py` / `messaging.py` / `scheduler.py`),
   and make the tool return a clear error string when that dependency isn't set.
3. Register it in `_get_tools()` — unconditionally for a base tool, or behind the
   relevant `config` flag (e.g. memory, multi-agent, scheduler) for an optional one,
   via `tools.append(...)`.
4. If the tool performs a dangerous action, consider adding its action type to the
   approval/security config (`security.require_approval`, `approval.requires_approval`)
   in `aethon/config.py`.
5. Add tests exercising the tool's actions.

## Commit and pull request conventions

- **Branch off `main`.** All PRs target `main`; CI triggers on pushes and PRs to it.
- **Keep PRs scoped.** One logical change per PR makes review and the
  `CHANGELOG.md` entry straightforward.
- **Write clear commit messages.** Use the imperative mood ("Add Slack adapter",
  not "Added"/"Adds"), a concise subject line, and a body explaining the *why*
  when it isn't obvious.
- **Update docs and the changelog.** When behavior or configuration changes, update
  the relevant file under `docs/` and add an entry to the `## [Unreleased]` section
  of `CHANGELOG.md`.
- **Respect the security model.** All listening services bind to `127.0.0.1` by
  default; never default a port to `0.0.0.0`. Don't commit secrets. See
  [`docs/development/SECURITY.md`](docs/development/SECURITY.md).
- **Make CI green before requesting review.** Every PR runs three jobs:
  - **test** — the matrix on **Python 3.10, 3.11, and 3.12**: `pip install -e ".[dev]"`,
    `ruff check --select E9,F63,F7,F82 aethon`, then `pytest -q`.
  - **build** — `python -m build` + `twine check dist/*` (the wheel and sdist must
    be valid) on Python 3.12.
  - **docker** — builds the Docker image (no push).

  Run the lint and test commands above locally so all three pass.

## Reporting bugs and requesting features

Open an issue at <https://github.com/mertozbas/aethon/issues>. Include your OS,
Python version, AETHON version (`aethon --version`), and — where relevant — the
output of `aethon doctor`, which reports your provider, model, provider
reachability, and memory configuration.

For **security vulnerabilities**, do not open a public issue — follow the private
reporting process in [`SECURITY.md`](SECURITY.md).