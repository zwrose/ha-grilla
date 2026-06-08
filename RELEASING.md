# Releasing ha-grilla

Releases are automated with [release-please](https://github.com/googleapis/release-please).
HACS installs from GitHub **Releases**, so cutting a release is what ships an
update to users. Do not bump versions or edit the changelog by hand.

## How it works

1. Land commits on `main` using [Conventional Commits](https://www.conventionalcommits.org/)
   — see `CONTRIBUTING.md`.
2. release-please keeps an open **release PR** that bumps both `pyproject.toml` and
   `custom_components/grilla/manifest.json` (`version`), and updates `CHANGELOG.md`.
3. **Merge the release PR.** release-please tags `vX.Y.Z` and creates a GitHub
   Release; HACS picks it up automatically.

## aiogrilla version coordination (important)

ha-grilla requires aiogrilla in `manifest.json`
(`requirements: ["aiogrilla>=X.Y.Z"]`), and the CI `test` job installs `aiogrilla>=X.Y.Z`
from PyPI (the latest compatible release). The floor is a **minimum**, so routine aiogrilla
releases need no ha-grilla change. Only when ha-grilla starts depending on a NEW aiogrilla
feature, raise the floor:

- Confirm that aiogrilla version is **published to PyPI**.
- Raise the `>=` floor in **both** `manifest.json` and `.github/workflows/ci.yml`, keeping
  them identical. (aiogrilla must be on PyPI before ha-grilla's CI can pass / users install.)
