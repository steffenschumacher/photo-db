# Repository Guidelines

## Project Structure & Module Organization

Core Python code lives in `photo_db/`. Important packages include `photo/` for image logic, `scanner/` for imports, `store/` and `db/` for persistence, and `client/`, `api/`, and `ui/` for access surfaces. The Angular companion is in `web-ui/`. Top-level entry points are `pdbscanner.py`, `photodb-ui.py`, and `photo_db.app:create_app`. Tests and image fixtures are under `test/`; architecture notes live in `docs/`.

## Build, Test, and Development Commands

- `uv sync` installs the core scanner dependencies.
- `uv sync --extra api` adds the Flask server; run it with `uv run flask --app photo_db.app:create_app run`.
- `uv sync --extra ui` adds PySide6; launch with `uv run python photodb-ui.py`.
- `uv run pytest` runs the normal test suite, excluding GUI and live-network tests.
- `QT_QPA_PLATFORM=offscreen uv run pytest -m gui` runs desktop UI smoke tests.
- `uv run ruff check .` and `uv run ruff format --check .` lint and verify formatting.
- `uv run pre-commit run --all-files` performs the complete CI-style hygiene check.
- `cd web-ui && npm ci && npm test -- --watch=false && npm run e2e && npm run build` verifies the Angular app and Chromium flow.

## Coding Style & Naming Conventions

Target Python 3.13 and use four-space indentation. Ruff enforces import ordering, correctness rules, a 100-character line length, and formatting. Use `snake_case` for Python functions and `PascalCase` for classes; use Angular/TypeScript defaults in `web-ui/`. Prefer explicit dependency injection over global configuration.

## Testing Guidelines

Use pytest and place tests in `test/test_<feature>.py`. Add regression tests with bug fixes and isolate stores/caches using fixtures and temporary directories. Mark tests requiring real windows with `gui` and external services with `network`. For meaningful changes, run `uv run pytest` plus the relevant focused test file. Coverage is configured for `photo_db`; avoid reducing coverage on changed code.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative summaries, optionally prefixed by an area such as `docs:`. Keep each commit focused and explain the user-visible outcome. Pull requests should describe behavior changes, tests run, configuration or migration impacts, and linked issues. Include screenshots for PySide6 or future web UI changes.

## Security & Configuration

Keep credentials in ignored `.env` files or runtime environment variables (`PH_STORE_USER`, `PH_STORE_PASS`); never commit tokens or photo libraries. Run the secret-detection pre-commit hooks before submitting changes.
