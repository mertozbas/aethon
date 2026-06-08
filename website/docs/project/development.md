---
id: development
title: Development
sidebar_label: Development
---

# Development

```bash
git clone https://github.com/mertozbas/aethon.git
cd aethon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run tests

The `e2e` marker spawns a subprocess and binds a socket; the `ollama` marker needs a
running Ollama.

```bash
pytest                       # full suite
pytest -q                    # quiet
pytest -m "not e2e"          # skip end-to-end boot tests
```

## Lint

The error-level gate CI enforces:

```bash
ruff check --select E9,F63,F7,F82 aethon
```

## CI

`.github/workflows/ci.yml` (name `CI`, on push/PR to `main`) runs three jobs:

- `test` — matrix on Python 3.10 / 3.11 / 3.12; `pip install -e ".[dev]"`; ruff error-level lint; `pytest -q`.
- `build` — `python -m build` + `twine check dist/*` on 3.12.
- `docker` — builds image `aethon:ci` (no push).

Contributions follow the same noncommercial terms; see
[CONTRIBUTING.md](https://github.com/mertozbas/aethon/blob/main/CONTRIBUTING.md).

## Documentation site

This handbook is a [Docusaurus](https://docusaurus.io) site under `website/`. To work
on it locally:

```bash
cd website
npm install
npm start                    # dev server with hot reload
npm run build                # production build into website/build
```

Translated content lives under `website/i18n/<locale>/`. The site deploys to GitHub
Pages automatically from `main` via `.github/workflows/docs.yml`.
