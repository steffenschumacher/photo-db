# PhotoDB

A client/server photo library consolidator with client-side duplicate
detection: photos are hashed (perceptual hash of a scaled-down image) and
checked against the target library's metadata/hashes *before* the full image
is uploaded, avoiding expensive uploads of photos that already exist.

Accepted photos are stored under `<library>/<year>/<month>/<filename>`, with
filenames derived from capture date/time so files sort chronologically and
stay unique.

## Status

This project is a work in progress. See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — design & how the pieces
  fit together.
- [`docs/PROJECT_STATUS_AND_PLAN.md`](docs/PROJECT_STATUS_AND_PLAN.md) — a
  full audit of what's implemented, known bugs, and a prioritized plan to
  finish the project (including tests, pre-commit hooks, and a Python
  3.13/`uv`/`ruff` toolchain modernization).

## Quick start (current, legacy setup)

> The dependency/tooling setup described here is being modernized — see the
> plan doc above. Until then:

```bash
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # client/scanner side
# or: pip install -r requirements-api.txt                 # server/API side

# Run a scan of a local folder into a local library folder:
python pdbscanner.py -s /path/to/photos/to/import -l /path/to/library

# Run the API server locally:
python manage.py
```

Configuration is via environment variables (see `.env` for local overrides,
`photo_db/config.py` for defaults): `PH_STORE_URL`, `PH_STORE_USER`,
`PH_STORE_PASS`, `PH_HASH_SIZE`, `PH_SIMILARITY`, `PH_UID`, `PH_GID`.

**Note:** the `.env` file checked into this working copy contains real
credentials for a personal server — treat these as compromised, rotate them,
and keep only an `.env.example` with placeholder values under version
control going forward (see the plan doc, Phase 0).

## Running tests

Tests currently must be run with `test/` as the working directory (this is
a known issue, tracked in the plan doc, Phase 1.3):

```bash
cd test
pytest
```

The two tests under `test/ui/` open real desktop GUI windows and will hang in
headless/CI environments — skip them for now (see plan doc, Phase 4.2).
