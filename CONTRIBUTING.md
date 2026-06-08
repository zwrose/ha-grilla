# Contributing to ha-grilla

Thanks for your interest in improving ha-grilla, an unofficial Home Assistant
integration for Grilla Grills Alpha Connect smokers.

## Development setup

This integration depends on the [aiogrilla](https://github.com/zwrose/aiogrilla)
library. A typical local setup:

```bash
git clone https://github.com/zwrose/ha-grilla.git
cd ha-grilla
python -m venv .venv
.venv/bin/pip install homeassistant pytest pytest-homeassistant-custom-component ruff pyright
.venv/bin/pip install aiogrilla   # or an editable checkout of a local aiogrilla
```

## Checks that must pass

All four gates run in CI and must pass locally before you open a pull request:

```bash
ruff check .
ruff format --check .
pyright
pytest -q
```

The integration is also validated by **hassfest** and the **HACS action** in CI;
both must pass. Installing the pre-commit hooks runs the formatters automatically:

```bash
pre-commit install
```

## Tests

Tests use `pytest-homeassistant-custom-component`. Write tests alongside new code.
Never include account identifiers or tokens in fixtures, diagnostics, or logs.

## Commit messages — Conventional Commits (required)

This repository uses [Conventional Commits](https://www.conventionalcommits.org/).
**This is required, not stylistic:** releases, the `CHANGELOG.md`, and the
`manifest.json` version bump are generated automatically by
[release-please](https://github.com/googleapis/release-please) from commit
messages.

Format:

```
type(optional-scope): short summary
```

Common types and their release effect:

| Type | Use for | Version effect |
|------|---------|----------------|
| `feat:` | a new capability | minor bump |
| `fix:` | a bug fix | patch bump |
| `docs:` | documentation only | none |
| `refactor:` | non-behavioral code change | none |
| `test:` | tests only | none |
| `chore:` / `ci:` / `build:` | tooling, CI, packaging | none |
| `perf:` | performance change | patch bump |

A `!` after the type (e.g. `feat!:`) or a `BREAKING CHANGE:` footer marks a
breaking change (major bump; while pre-1.0, treated as a minor bump).

Examples:

```
feat: add a sensor for the meat probe target temperature
fix: keep the connectivity sensor available when the grill goes offline
docs: clarify the HACS install steps
chore: bump aiogrilla to 0.2.0
```

If you open a PR with multiple commits, the **PR title** must also be a valid
Conventional Commit, because PRs are squash-merged using the title.

## Pull requests

- Keep changes focused; one logical change per PR.
- Make sure the four checks plus hassfest/HACS validation pass.
- Update or add tests for behavior changes.
- The maintainer reviews and merges; thanks for your patience.
