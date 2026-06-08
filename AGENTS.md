# AGENTS.md — AI assistant guidance for ha-grilla

## Project purpose

Unofficial read-only Home Assistant custom integration (domain `grilla`) for
Grilla Grills Alpha Connect smokers. Exposes live telemetry — temperatures, cook
status, cook mode, cook timer, problem/probe-present/connectivity binary sensors,
and an alarm event entity — via the `aiogrilla` library.

## Layout

```
custom_components/grilla/
    __init__.py        — integration setup/teardown and GrillaConfigEntry runtime_data
    const.py           — domain constant, platform list, config/options keys
    coordinator.py     — GrillaCoordinator: push DataUpdateCoordinator (no polling)
    entity.py          — GrillaEntity: shared base (unique_id, device_info)
    models.py          — GrillaConfigEntry, GrillaRuntimeData type aliases
    sensor.py          — temperature, status, cook_mode, cook_timer sensors
    binary_sensor.py   — connectivity, problem, probe_present, probe2_present
    event.py           — GrillaAlarmEvent (rising-edge alarm/temp-range transitions)
    config_flow.py     — GrillaConfigFlow (user + reauth) and GrillaOptionsFlow
    diagnostics.py     — async_get_config_entry_diagnostics (credentials redacted)
    strings.json       — translation strings (English)
    translations/      — per-locale JSON translation files

tests/
    conftest.py        — shared fixtures (mock aiogrilla client, config entry)
    test_*.py          — unit tests, no live network
```

## Hard boundary

**ha-grilla must NEVER import `boto3`, `awscrt`, `awsiot`, `botocore`, or
`pycognito`.** All AWS Cognito authentication and AWS IoT/MQTT access goes through
the `aiogrilla` library. This boundary is enforced at lint time by ruff's
`flake8-tidy-imports` banned-api rules in `pyproject.toml` — a violation is a
lint error, not just a style nit.

Note: `manifest.json`'s `loggers` field intentionally lists aiogrilla's
transitive AWS dependency logger names (`awscrt`, `awsiot`, `pycognito`, `boto3`,
`botocore`) so users can capture full auth/MQTT debug logs when troubleshooting.
This is log-namespace relaying, NOT a direct import or a boundary violation — the
banned-import rule governs ha-grilla's own imports only, and ha-grilla never
imports any of these modules.

## Architecture

ha-grilla is a **thin HA layer over aiogrilla**:

- `GrillaCoordinator` wraps `GrillaClient.on_state` and
  `GrillaClient.on_availability`. It sets `update_interval=None` (no polling);
  HA entities are notified only when the library pushes a new state or
  availability change.
- Off-detection (going unavailable, transitioning back to available) is owned
  entirely by aiogrilla, not by this integration.
- Entities derive from `GrillaEntity` which inherits
  `CoordinatorEntity[GrillaCoordinator]`. All data access goes through
  `self.coordinator.data` (a `GrillState | None`) and
  `self.coordinator.grill_available` (a `bool`).

## Off-at-startup None-safety invariant

**`coordinator.grill_available == True` does NOT imply `coordinator.data is not
None`.**

When HA starts while the grill is connected but not currently firing telemetry,
the coordinator marks itself available before any state has arrived. Every
property that derives a value from `coordinator.data` must guard for `None`:

```python
# correct
d = self.coordinator.data
return None if d is None else d.grill_temp

# wrong — will raise AttributeError if data has not arrived yet
return self.coordinator.data.grill_temp
```

This invariant is tested in `tests/test_sensor.py` and `tests/test_binary_sensor.py`.

## Dev setup

```bash
python3 -m venv .venv
.venv/bin/pip install homeassistant pytest pytest-homeassistant-custom-component ruff pyright aiogrilla
# (to co-develop the library too, install it editable instead: pip install -e /path/to/aiogrilla)
```

## Gate commands

All four must pass cleanly before committing or opening a PR:

```bash
.venv/bin/pytest -q          # run the test suite (41 tests, no live network)
.venv/bin/ruff check .       # lint (includes banned-api enforcement)
.venv/bin/ruff format --check .  # formatting
.venv/bin/pyright            # type-check
```

## Read-only scope

v1 of this integration is monitoring only. Do not add write operations (service
calls, setpoints, start/stop) — they are intentionally out of scope.

## Secrets and credentials

The Cognito refresh token is stored in the HA config entry data under the key
`refresh_token`. It must never be logged, included in test fixtures, or committed
to the repository. Diagnostics are redacted before export.

## TDD expectation

Write tests before or alongside new logic. New entity behavior, coordinator
transitions, and config-flow paths should be covered by unit tests using fixtures
or mocks — no live network calls in the test suite.

## Commit messages — Conventional Commits (required)

Every commit on `main` and every squash-merged PR title MUST be a
[Conventional Commit](https://www.conventionalcommits.org/). This is load-bearing:
`release-please` derives the version bump, `CHANGELOG.md`, and the
`manifest.json` version from these messages.

- `feat:` → minor bump · `fix:`/`perf:` → patch bump · `docs:`/`refactor:`/`test:`/`chore:`/`ci:`/`build:` → no release
- `feat!:` or a `BREAKING CHANGE:` footer → major bump (minor while pre-1.0)
- Examples: `feat: add probe target temperature sensor`, `fix: keep connectivity sensor available when offline`

See `CONTRIBUTING.md` for the full table. Do not write non-conventional commit
messages in this repo.
