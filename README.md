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
dependency-injected `Config`, thumbnail generation + a lean, incrementally-
syncable local metadata cache (the foundation of the desktop UI, see below),
a PySide6 desktop "thick client", a real test suite (60+ tests), and
pre-commit hooks + CI. See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — design & how the pieces
  fit together.
- [`docs/PROJECT_STATUS_AND_PLAN.md`](docs/PROJECT_STATUS_AND_PLAN.md) — the
  original audit (bugs found, component status) plus a completion summary at
  the top describing what was actually built and a few decisions that
  differ from the initial proposal.

## Desktop UI (thick client)

`photo_db/ui/` is a PySide6 (Qt) desktop app for maintaining a photo library
both locally and against a remote web backend. **Scan folder..**, **Sync
library..**, and **Settings..** are available both from the menu bar *and*
a toolbar (menus alone are easy to miss on macOS, where they live in the
global system menu rather than in the window), and the status bar always
shows which store is currently active (`Store (local|remote): <path/url>`):

- **Scan folder..** recursively scans a chosen directory and adopts any
  photos not already present in the configured store (local path or remote
  webservice), reusing the same `Scanner`/duplicate-detection pipeline as
  `pdbscanner.py`, with a live progress table.
- **Sync library..** pulls incremental metadata (no image bytes) from the
  central store into a local sqlite "lean cache"
  (`photo_db/db/lean_cache.py`), so the client can determine locally
  whether a candidate photo already exists (cheap duplicate pre-check
  before hashing) and browse the library offline.
- The central thumbnail grid browses the lean cache by year/month (picker)
  and infinite scroll, lazily fetching ~300k-pixel thumbnails
  (`photo_db/photo/thumbnail.py`, generated server-side at upload time,
  served via `GET /thumb/<uuid>`) in background threads as they scroll into
  view, with a small on-disk client-side cache. Thumbnails and the full
  image are always shown auto-rotated per EXIF orientation.
- **Double-clicking a thumbnail** opens a full-image preview
  (`ImageViewerDialog`) with "Rotate left"/"Rotate right" buttons; rotating
  persists back to whichever store is configured (local or remote) and
  refreshes the corresponding thumbnail immediately.
- **Settings..** edits `Config` (store URL/credentials, hash size,
  similarity threshold, lean cache path) and persists changes to `.env`.
  Saving takes effect immediately — the store (local or remote), lean
  cache, and thumbnail grid are all reloaded in place, no restart needed.
  A brand new local folder path is a valid choice (created on demand); if
  no valid store is configured yet, the window shows a placeholder with a
  direct link back to Settings instead of a dead end.

Requires the `ui` extra (`uv sync --extra ui`); launch with:

```bash
uv run python photodb-ui.py
```

wxPython was the original (abandoned) choice for this UI; PySide6 was
chosen for the rewrite for its LGPL licensing and `QListView`/
`QAbstractListModel`/`QThreadPool` support, which is the idiomatic Qt
pattern for a virtualized, lazily-loaded thumbnail grid.

## Quick start

Requires Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).

```bash
# Install dependencies (client/scanner only):
uv sync

# ...or include the optional extras you need:
uv sync --extra api    # Flask HTTP API server
uv sync --extra raw    # Sony .ARW (and similar) RAW photo conversion
uv sync --extra ui     # PySide6 desktop "thick client"

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
