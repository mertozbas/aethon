# Releasing AETHON

Releases are **automatic on a version bump**. The
[`Release` workflow](.github/workflows/release.yml) runs on every push to
`main`: it reads `project.version` from `pyproject.toml`, and if no
`v<version>` tag exists yet it runs the test suite, builds the distribution,
publishes it to PyPI as **`aethon-ai`**, and creates the matching git tag +
GitHub Release. Bumping the version is the only trigger.

Because the publish is automatic, the version bump must be the **last** step,
after the changelog and version files are consistent. Do these in order, in a
single release commit:

## 1. Bump the version (two files, together)

The version string lives in exactly two places — keep them identical:

- `pyproject.toml` → `project.version`
- `aethon/__init__.py` → `__version__`

(`aethon --version`, the `/api/status` endpoint, and the dashboard all read
`aethon.__version__`, so this one bump propagates everywhere.)

Use [semantic versioning](https://semver.org/): a feature release bumps the
minor (`0.2.0 → 0.3.0`), a fix-only release bumps the patch.

## 2. Cut the changelog

In [`CHANGELOG.md`](CHANGELOG.md):

- Rename the `## [Unreleased]` heading to `## [<version>] - <YYYY-MM-DD>` and
  leave a fresh, empty `## [Unreleased]` above it for the next cycle.
- Update the compare-link footer at the bottom of the file: point
  `[Unreleased]` at `compare/v<version>...HEAD`, and add a
  `[<version>]: .../compare/v<prev>...v<version>` row.

## 3. Update the supported-versions table

In [`SECURITY.md`](SECURITY.md), bump the **Supported versions** table to the
new `<minor>.x` line — it is the canonical security-policy version and is linked
from several docs.

## 4. Commit, push, watch

Commit all of the above together (e.g. `chore(release): v0.3.0`), push to
`main`, and watch the `Release` workflow. It gates on the test suite, so a red
suite blocks the release. On success it publishes to PyPI and creates the tag +
GitHub Release; the install is `pip install aethon-ai` (the import and CLI stay
`aethon`).

> If the workflow finds the tag already exists, it does nothing — re-running a
> push without a version bump never re-publishes.
