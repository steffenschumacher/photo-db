# PhotoDB

A client/server photo library consolidator with client-side duplicate
detection: photos are hashed (perceptual hash of a scaled-down image) and
checked against the target library's metadata/hashes *before* the full image
is uploaded, avoiding expensive uploads of photos that already exist.

Duplicate detection first checks cheap metadata (capture date, dimensions)
and only computes/compares the perceptual hash when needed, so resized/
re-encoded copies of an already-stored photo are still recognized as
duplicates without a byte-for-byte comparison.

Accepted photos are stored under `<library>/<YYYY>/<MM>/<filename>`, with
zero-padded year/month folders and filenames prefixed with a fixed-width
numeric capture timestamp (day-of-month + hour + minute + second +
millisecond) so files sort chronologically by capture date within each
month, while staying unique (a short suffix from the photo's UUID
disambiguates same-millisecond collisions, e.g. burst shots).

## Status

All phases of the modernization/completion plan have been implemented:
Python 3.13 + `uv` + `ruff` toolchain, pydantic v2, bug fixes (SQL injection/
syntax bugs, swallowed upload errors, hardcoded credentials, `send_file`
crash), the intended naming/foldering scheme, HEIC EXIF read/write, RAW
(`.ARW`) conversion wired into the scan pipeline, a fully instance-based/
dependency-injected `Config`, a real test suite (40 tests, 67% coverage),
and pre-commit hooks + CI. See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — design & how the pieces
  fit together.
- [`docs/PROJECT_STATUS_AND_PLAN.md`](docs/PROJECT_STATUS_AND_PLAN.md) — the
  original audit (bugs found, component status) plus a completion summary at
  the top describing what was actually built and a few decisions that
  differ from the initial proposal.

The wxPython desktop UI (`photo_db/ui/`) remains an unfinished prototype by
explicit decision — the CLI (`pdbscanner.py`) and Flask HTTP API are the
supported ways to use this project; only trivial lint/bug fixes were applied
to the UI code, no new UI functionality was added.

## Quick start

Requires Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).

```bash
# Install dependencies (client/scanner only):
uv sync

# ...or include the optional extras you need:
uv sync --extra api    # Flask HTTP API server
uv sync --extra raw    # Sony .ARW (and similar) RAW photo conversion

# Run a scan of a local folder into a local library folder:
uv run python pdbscanner.py -s /path/to/photos/to/import -l /path/to/library

# ...or into a remote webservice-backed library:
uv run python pdbscanner.py -s /path/to/photos/to/import \
    -l https://photodb.example.com -u myuser -p mypassword

# Run the API server locally (requires the `api` extra):
uv run flask --app photo_db.app:create_app run
```

Configuration is via environment variables (see `.env.example` for the full
list, `photo_db/config.py` for defaults and precedence): `PH_STORE_URL`,
`PH_STORE_USER`, `PH_STORE_PASS`, `PH_HASH_SIZE`, `PH_SIMILARITY`, `PH_UID`,
`PH_GID`. `Config` is an instantiable class (`photo_db.config.Config`) — env
vars are only the default source; any value can be overridden explicitly
per-instance (e.g. for tests, or running multiple independent configs in one
process), and a shared `photo_db.config.default_config` instance is used
anywhere a config isn't explicitly passed.

**Note:** if the `.env` file in this working copy ever contained real
credentials for a live server, treat them as compromised and rotate them —
the hardcoded credential fallbacks that used to live in `Config` have been
removed, but rotating the credentials themselves is outside what this
tooling can verify or action.

## Running tests

```bash
uv run pytest
```

By default this excludes tests marked `gui` (open real desktop windows) and
`network` (hit live third-party services, e.g. the geocoding tests against
the public Nominatim API). To run everything, including network tests:

```bash
uv run pytest -m ""
```

With coverage:

```bash
uv run pytest --cov=photo_db --cov-report=term-missing
```

## Linting & formatting

```bash
uv run ruff check .
uv run ruff format .
```

## Pre-commit hooks

```bash
uv run pre-commit install       # one-time, sets up the git hook
uv run pre-commit run --all-files   # run manually against the whole repo
```

Hooks include `ruff` (lint + format), standard hygiene checks, and
`detect-secrets` (given the real leaked credentials found in this project's
history — see the plan doc, §2.4).

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `uv sync`, `pre-commit run
--all-files`, the test suite with coverage, and `ruff check`/`ruff format
--check` on every push/PR to `main`.
