@AGENTS.md

## Claude-specific notes
- Run the test suite with `.venv/bin/pytest -q` before committing.
- Lint/format/type: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and `.venv/bin/pyright`.
- Never read or commit real Grilla account credentials or refresh tokens.
- Do not import `boto3`, `awscrt`, `awsiot`, `botocore`, or `pycognito` — use `aiogrilla`.
- **Commit messages MUST be Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:`, `feat!:`/`BREAKING CHANGE:` …); release-please derives versions, the changelog, and the `manifest.json` bump from them. See `AGENTS.md` / `CONTRIBUTING.md`.
