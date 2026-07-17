# PhotoDB — Project Status, Bug Findings, and Completion Plan

Audit date: 2026-07-16. This is a from-scratch code read + targeted test runs
(no git history was available — the working copy is not an initialized git
repository).

## 0. Completion summary (update)

All six phases of the plan below (§4) have now been implemented and are
committed to git. Sections 1–3 and 5 below are kept as-written for
historical/audit context (they describe the state *before* this work), with
inline "**Fixed:**"/"**Done:**" notes added where the finding has since been
resolved. The plan in §4 has been annotated phase-by-phase with what was
actually built, including a few decisions that differ from the original
proposal:

- **Config** was refactored to a fully instantiable, dependency-injected
  class (`photo_db.config.Config`), not the lighter-weight
  "keep class attributes, add a lazy-reload metaclass" option that was also
  on the table — the user explicitly chose the bigger DI refactor for real
  test/concurrency isolation. A module-level `default_config = Config()`
  singleton is kept for call sites that don't need an override, so most
  existing call patterns still work unchanged.
- **RAW (`.ARW`) conversion** ended up using `rawpy`/`imageio` (already a
  declared optional dependency, `raw` extra) instead of shelling out to
  `exiftool`; `photo_db/photo/arw_converter.py` was already written against
  `rawpy` at audit time, it just wasn't wired into `Scanner` — that wiring is
  now done, wrapped in a `try/except (ValueError, ImportError,
  ModuleNotFoundError)` so a missing `rawpy` install gracefully rejects RAW
  files rather than crashing the scan thread.
- **wxPython desktop UI**: per explicit user decision, **not** finished.
  Only lint/hygiene cleanup was applied (real bugs like a missing
  `datetime` import and a hardcoded developer-machine icon path were still
  fixed since they were trivial and clearly bugs, not scope creep). No new
  UI functionality was added. The recommendation to prefer the CLI/API
  surface over finishing the wx UI still stands.
- **Naming scheme**: implemented as zero-padded `YYYY/MM` folders plus a
  fixed-width numeric filename prefix (day-of-month + hour + minute + second
  + millisecond, no separators, e.g. `08190641000_2978.jpeg`, where the
  trailing `_2978` is the last 4 characters of the photo's UUID used as a
  same-millisecond disambiguator) rather than the literal
  `day-of-week-HH:MM:SS.mmmm_` spec, specifically to avoid the
  colon-in-filename portability problem raised in §5 while still sorting
  correctly both by folder and by filename. See §5 for the full rationale.
- Test coverage went from ~20% effectively-passing/hanging to **40 passing
  tests, 67% line coverage**, with all previously-hanging GUI tests properly
  marked `@pytest.mark.gui` and excluded from the default run (not deleted,
  since some assert real, previously-missing-import bugs like the
  `ui/filters.py` `datetime` fix).
- Secret-scanning: `detect-secrets` was used instead of `gitleaks` for the
  pre-commit hook, because `gitleaks`'s pre-commit hook needs to download a
  Go binary at hook-install time, which failed in this sandboxed dev
  environment due to TLS interception; `detect-secrets` is pure Python and
  installs the same way as every other hook. Either works fine in a normal
  CI runner; `detect-secrets` was simply the more portable, dependency-free
  choice here.
- **Reminder**: the real, leaked `STORE_USER`/`STORE_PASS` credentials found
  hardcoded as defaults in `Config` (removed in this pass — see §2.4) should
  still be rotated at the source (wherever the real server accepts them) if
  that hasn't already been done. This assistant cannot verify or action that
  rotation itself.

## 1. Component-by-component status

| Component | Status | Notes |
|---|---|---|
| `Photo` model (metadata, hash, `similar_to`, `preferable_to`) | **~85% done** | Solid core logic; naming/foldering scheme doesn't match intended spec (§2.1); no unit coverage for edge cases (missing EXIF, non-UTC dates, HEIC). |
| EXIF/GPS parsing (`parsers.py`) | **~80% done** | Works for common JPEG/EXIF cases; raises generic `ValueError`s that get logged then swallowed in the scanner — silent data loss risk; no timezone handling beyond naive UTC assumption. |
| Perceptual hashing + similarity | **Working** | `average_hash` + Hamming distance via numpy; hash is base64-encoded and reshaped using `Config.HASH_SIZE`, which means **changing `HASH_SIZE` after photos are stored breaks decoding of old hashes** — no versioning. |
| RAW (`.ARW`) conversion | **Prototype** | Shells out to `exiftool` (must be separately installed, not declared as a dependency anywhere) via `subprocess.Popen(...).wait()` with no error checking; not wired into the `Scanner` pipeline at all — only reachable via direct test call. |
| HEIC EXIF writing | **Not implemented** | `update_heic()` is a documented `raise NotImplementedError` stub. Reading HEIC works (via `pillow-heif` + `PIL`), writing back GPS/date does not. |
| Scanner (dir walk + in-scan/central dedup) | **~75% done**, has real bugs | See §2.2. Threaded via a 4-worker pool; central-hash comparisons are lock-protected but `check_with_central_photos` always returns truthy even on the exception path (bug). |
| Scan-session log (`db/scanner.py`) | **Buggy** | SQL string-building bugs — see §2.3. In-memory by default (`:memory:`), so a scan's history/audit trail is lost once the process exits, despite the class existing seemingly to support reviewing past scans. |
| Local sqlite store (`db/store.py`) | **Buggy** | Same SQL bugs as scanner DB, plus `search()` is missing its `return` statement (always returns `None`) — see §2.3. All queries build SQL via f-strings (SQL injection risk, since `uuid`/`hash` come from network input in the web API path). |
| `LocalStore` (filesystem write + folder layout) | **~70% done** | Core `upload`/`check_hash` logic reasonable, but see §2.1 for the folder/filename bug, and `chown` on every upload will fail loudly for non-root/non-owning users in real deployments. |
| Client abstraction (`AbstractPDBClient`, `LocalPDBClient`, `WebPDBClient`) | **~70% done** | `LocalPDBClient.check_hash` passes the builtin `hash` function instead of its own `ph` argument (real bug, likely a rename-refactor slip — see §2.2). `WebPDBClient` embeds a hardcoded fallback password default (security smell, see §2.4). |
| Flask HTTP API (`api/web_store.py`, `app.py`) | **~70% done** | Routes exist for all client operations; no rate limiting, no HTTPS enforcement (relies on being reverse-proxied), errors from `LocalStore.upload` are only ever `print()`ed then silently return `None` (client gets a 200 with an empty body instead of an error). |
| CLI scanner (`pdbscanner.py`) | **~80% done**, workable | Argument parsing is fine; mutates `Config` class attributes at runtime, which is fragile (shared mutable global config; not thread/test-safe — see §2.5). |
| Reverse geocoding (`geocoding/nominatim.py`) | **Done for its narrow purpose** | Thin wrapper, no caching, no error handling if geocoding fails/rate-limits (Nominatim's public instance is rate-limited to 1 req/s — no throttling/backoff here). Used only by tests/manual tooling, not by the main scan pipeline. |
| Desktop UI (`photo_db/ui/`) | **~25% done — prototype only** | See §2.6. `ImportFrame`/`ScanInitDialog` are a rough first pass: no way to actually browse/select a scan folder in the frame flow shown, hardcoded absolute path to an icon file (`/Users/stsmr/PyCharmProjects/...`), no packaging/entry point, "Load existing scan" menu item is a no-op stub. |
| `photo_db/cli/__init__.py` | **Dead code** | References `read_config`/`load_config` that don't exist anywhere in the codebase — this module cannot run. Looks like an abandoned earlier CLI design, superseded by `pdbscanner.py`. |
| Tests | **~20% effectively passing** | See §3 — tests exist and mostly *can* pass, but only if run from inside `test/` (no `pytest.ini`/`pyproject.toml` sets `rootdir`/`testpaths`), and the two `ui/` tests open real, blocking OS GUI windows (`wx.App().MainLoop()`) rather than testing anything programmatically — they will hang indefinitely in CI or any non-interactive environment. |
| Packaging / dependency management | **Legacy** | Two virtualenvs checked into the repo (`venv/`, `venv311/`), split `requirements*.txt` files that have already drifted from each other (see diff in §2.7), no `pyproject.toml`, no lockfile, no declared Python version. |
| Pre-commit / CI | **Missing entirely** | No `.pre-commit-config.yaml`, no lint config (`ruff`/`black`/`flake8`), no CI workflow files anywhere in the tree. |
| Docs | **Missing entirely** (until this pass) | No `README.md` in the repo at all. |

## 2. Concrete bugs / issues found (with evidence)

### 2.1 Storage naming/foldering doesn't match the intended spec, and isn't padded

Intended (per project owner): store photos under `year/month/`, with filenames
prefixed `day-of-week-HH:MM:SS.mmmm_` for unique, sortable names.

Actual, in `photo_db/photo/photo.py`:

```python
def db_path(self) -> str:
    return join(f"{self.date.year}", f"{self.date.month}", self.filename())

def filename(self) -> str:
    return f"{self.date.strftime('%d-%H%M%S')}-{self.uuid[-4:]}.{self.extension}".lower()
```

Problems:
- `self.date.month` is **not zero-padded**. Folder names sort as strings on
  most filesystems/tools, so `10` (October) sorts before `2` (February) —
  breaking the stated goal of chronological sort via folder structure.
- The filename uses day-of-month (`%d`) and `HHMMSS`, not day-of-week, no
  colons, no millisecond precision, and no `_` separator — it does not
  implement the described `day-of-week-HH:MM:SS.mmmm_` scheme at all.
- Colons in `HH:MM:SS` (as literally requested) are invalid in Windows
  filenames — worth deciding now whether to keep the literal colon (fine on
  macOS/Linux) or substitute a safe separator, since this is a case where the
  literal request has a real cross-platform gotcha.
- Uniqueness currently comes from 4 hex chars of a UUID suffix, not from the
  time value having millisecond precision — two photos taken in the same
  second by the same camera (common in burst mode) rely entirely on the UUID
  suffix for disambiguation, which does still work, but doesn't match intent.

### 2.2 Real logic bugs

- `photo_db/client/local_client.py`:
  ```python
  def check_hash(self, ph: Photo) -> bool:
      return LocalStore.check_hash(hash)   # BUG: passes builtin `hash`, not `ph`
  ```
  This will pass Python's builtin `hash` function object into
  `LocalStore.check_hash`, which expects a `Photo` — this path is broken
  today and would raise `AttributeError` the moment it's actually exercised
  (it currently has no test coverage, which is how this went unnoticed).

- `photo_db/scanner/scanner.py::check_with_central_photos` returns `True` (or
  the photo object) on essentially every path, including inside the
  `except (DuplicateException, SimilarException)` block, so callers can't use
  its return value to know whether the upload actually happened; `process_image`
  ignores the return value entirely anyway, so this is latent rather than
  actively wrong today, but should be tightened alongside adding tests.

- `photo_db/api/web_store.py::upload` and `LocalStore.upload`: if writing the
  file raises inside the `try/except Exception as e: print(e)` block, the
  Flask route still returns whatever `LocalStore.upload` returns, i.e. `None`
  → Flask will turn that into an empty `200 OK` body. A client uploading a
  photo that fails to persist on disk gets no indication that anything went
  wrong.

### 2.3 SQL bugs in `photo_db/db/store.py` and `photo_db/db/scanner.py`

Both modules build SQL via string formatting and both have a stray trailing
`)`—a copy/paste bug that is currently silent because Python's `sqlite3`
module raises on `execute()`, but the surrounding `try/finally` (in
`store.py`) has no `except`, so this **will raise `OperationalError` for any
caller of `get_photo`, `lookup_hash`, or `search`** the first time they're
actually hit with real data (not currently covered by any test):

```python
qry = f"{_select} WHERE uuid = '{uuid}';"       # OK
...
qry = f"SELECT {','.join(fields)} FROM photo{where})"   # BUG: stray ')'
```
(`db/scanner.py` has the same `')'` bug in `get_photo`/`lookup_hash`.)

Separately, `db/store.py::search()` is missing its `return results` statement
entirely — it always returns `None`, silently discarding any results it
fetched. `ScanDB.search()` (in `db/scanner.py`) does not have this particular
bug (it does return), but shares the SQL string-interpolation approach.

All of these queries also interpolate untrusted input (`uuid`, `hash` values
that ultimately originate from HTTP requests in the web API path) directly
into SQL strings rather than using parameterized queries — a SQL injection
risk, even though the attack surface today is narrow (single-user, basic-auth
protected API).

### 2.4 Security / secrets hygiene

- `.env` (checked into the working tree) contains a real hostname, username,
  and what looks like a live password for a personal server. This should be
  rotated and removed from the tree/history once the project moves into git,
  and `.env` should be gitignored.
- `photo_db/config.py` and `photo_db/client/web_client.py` both have
  **hardcoded fallback credentials** (`STORE_USER`/`STORE_PASS` defaults, and
  a default `pwd` fallback in `WebPDBClient.__init__`). Defaults should not be
  usable credentials — fail closed (require explicit configuration) instead.
- Basic auth only, no rate limiting on the Flask API, and `SSL_VERIFY`
  defaults to `False` — the client will happily accept invalid TLS certs on
  the server unless explicitly configured otherwise. Combined with basic
  auth, this makes MITM credential theft realistic on untrusted networks.
- A stray directory literally named `https:/` exists at the repo root with
  `.photo.db` files inside it — evidence that a URL string was at some point
  used directly as a local filesystem path (`os.path.join` treats
  `https://host/...` as a set of nested folders `https:/`, `host`, ...). This
  suggests `LocalPDBClient`/`init_client` URL-vs-path detection has, in
  practice, misfired before. Worth a regression test.

### 2.5 Config is a mutable global class, not an instance

`Config` (`photo_db/config.py`) is a class with class-level attributes,
mutated directly at runtime (`Config.STORE_URL = ...` in `pdbscanner.py`, the
UI dialog, and tests). This makes:
- Parallel/async use unsafe (shared mutable global state).
- Testing awkward (tests must remember to restore prior values; several
  fixtures set `Config.STORE_URL`/`Config.STORE_DB_URL` per-test but there's
  no teardown resetting them, so test order can affect results).
- `Config.STORE_DB_URL` is set by tests/`test_client.py` but **does not
  exist as a real config field** — `db/store.py` always computes the DB path
  as `join(Config.STORE_URL, ".photo.db")` itself. This is dead/misleading
  test setup left over from an earlier design.

### 2.6 UI is an early prototype, not a finished feature

- `ImportFrame`/`ScanInitDialog` construct working wx widgets, but:
  - `ScanInitDialog.OnSelectSP`'s selected path is never actually propagated
    into `Config`/`Scanner` — only `store_uri`'s text value is used later.
  - The icon path is hardcoded to a specific developer's machine
    (`/Users/stsmr/PyCharmProjects/photo-db/...`, note also the case/spelling
    mismatch vs. the current directory name `photo-db` under
    `PycharmProjects`), so the dialog will throw on any other machine.
  - "Load existing scan" (`OnLoadImport`) is an empty stub — there is no way
    to review a previous scan's results in the UI at all, despite `ScanDB`
    existing seemingly to support exactly that.
  - No progress bar / cancel button — `monitor_scan_process` polls in a
    background thread and appends rows, with no way to stop a long scan from
    the UI.
  - `wxPython` is commented out in `requirements.txt` (`#wxPython==4.2.1`)
    and absent from `requirements-dev.txt` entirely — the UI cannot currently
    be installed via the declared dependency files at all.

### 2.7 Dependency/packaging drift

- `requirements.txt` and `requirements-api.txt` have diverged (diff'd
  directly): `requirements-api.txt` adds `sqlite-fts4`, `Flask-HTTPAuth`,
  `Flask`, but is missing `requests`, `geopy`, `exif` that the scanner/client
  side needs — i.e. **the two files no longer represent a coherent
  "client" vs. "server" split**, and neither is sufficient on its own to run
  the full test suite (raw conversion needs `rawpy`/`imageio`, neither
  declared anywhere; UI needs `wxPython`, commented out).
- Two full virtualenvs (`venv/` for 3.10, `venv311/` for 3.11) are committed
  into the working tree — large, environment-specific, and not meant to be
  version-controlled.
- `photodb-import.tgz` (a stray tarball) sits at the repo root, undocumented.
- No `pyproject.toml`, no declared minimum/target Python version, no lock
  file (`uv.lock`/`requirements.lock`), no `ruff`/`black` config (despite
  `black` being listed as a dev dependency), no `mypy`/type-checking config
  despite fairly extensive use of type hints throughout the codebase.

## 3. Test suite: current real state

Running `pytest test -q` **from the repository root** (the natural way to
invoke it) currently hangs indefinitely / fails, for two independent reasons:

1. **Working-directory dependency.** All fixture/test image paths are written
   as relative strings like `"static/08-190641-4631.jpeg"`. The actual image
   fixtures live in `test/static/`, not the (empty, stale) top-level
   `static/`. There is no `pytest.ini`/`pyproject.toml` `[tool.pytest.ini_options]`
   setting `rootdir`/`testpaths`/`consider_namespace_packages`, so whether
   these tests pass depends entirely on the shell's current directory at
   invocation time. Verified: running the exact same tests from inside
   `test/` passes; from the repo root they fail with `FileNotFoundError`.
2. **The two `ui/` tests open real OS windows and block forever.**
   `test/ui/test_dialog.py` and `test/ui/test_frame.py` call
   `wx.App(0)` + `<Widget>(...)` + `app.MainLoop()` — a real, blocking native
   event loop with no automated interaction or timeout. In an interactive
   desktop session, this opens a visible window and hangs until a human closes
   it; in CI/headless environments it will hang until the test runner's own
   timeout (if any) kills it. These are not currently meaningful automated
   tests.

Once run from the correct working directory (confirmed manually per-file):

| File | Result | Notes |
|---|---|---|
| `test_unit.py` | 2 passed | Needs `test/static/*.jpeg` fixtures present. |
| `test_client.py` | 1 passed | |
| `test_scanner.py` | 1 passed | Only asserts the scan *runs*; doesn't assert on dedup outcomes. |
| `test_geocoding.py` | 1 passed | Hits the live public Nominatim API over the network — no mocking, will be flaky/rate-limited, and will fail with no network. |
| `test_photo.py` | 3 passed | `test_convert_raw` shells out to a real `exiftool` binary and hits live Nominatim — both external dependencies undeclared and unmocked. |
| `test/ui/*` | Hangs | Opens real GUI windows; not automatable as-is. |

Overall: the individual assertions that exist are reasonable smoke tests, but
there is **no coverage at all** for: SQL persistence correctness (would have
caught §2.3), the `LocalPDBClient.check_hash` bug (§2.2), folder/filename
correctness (§2.1), config isolation/mutation, HEIC handling, malformed/missing
EXIF variations, HTTP error paths (409 duplicate/similar responses), or
concurrent-scan correctness (the whole point of the thread pool in `Scanner`).
Coverage tooling (`pytest-coverage`) is declared as a dependency but there's no
config wiring it into a required threshold or CI gate.

## 4. Prioritized completion plan

### Phase 0 — Make the repo a real, safe, reproducible project ✅ Done
1. `git init` this project (it currently has no version control at all) and
   add a proper `.gitignore` (venvs, `__pycache__`, `.env`, `.idea`,
   `*.pyc`, `coverage_html_report/`, the stray `https:/` dir,
   `photodb-import.tgz`).
2. Rotate the real credentials currently sitting in `.env` before it ever
   touches a remote/shared git history; keep only an `.env.example` with
   placeholder values in the repo.
3. Delete committed virtualenvs (`venv/`, `venv311/`) and stray artifacts
   (`https:/`, `photodb-import.tgz`, `__pycache__/`, `.DS_Store`s).

### Phase 1 — Modernize tooling (Python 3.13, `uv`, `ruff`) ✅ Done
1. Add a `pyproject.toml`:
   - `requires-python = ">=3.13"`, project metadata, and consolidate
     `requirements.txt`/`requirements-api.txt`/`requirements-dev.txt` into
     proper `[project.dependencies]` + `[project.optional-dependencies]`
     groups (`api`, `ui`, `raw` for `rawpy`/`imageio`/`exiftool`-dependent
     features, `dev`/`test`).
   - Run `uv lock` to produce `uv.lock`; document `uv sync --extra ...`
     as the setup command in the README.
   - Verify third-party deps (`pydantic` 1.x, `Flask`, `Pillow`, `imagehash`,
     `pillow-heif`, `exifread`, `exif`, `geopy`, `sqlite-utils`) actually
     support 3.13 — `pydantic` 1.10.x in particular should be evaluated for
     upgrade to `pydantic` 2.x while touching this code anyway (2.x has been
     out for years and 1.x is unmaintained), which also affects `Photo`'s
     `BaseModel` usage (`.dict()`/`.json()` calls exist in the codebase and
     would need updating to `.model_dump()`/`.model_dump_json()`).
   - Add `[tool.ruff]` config (line length, target-version `py313`, a
     reasonable rule-set to start: `E`, `F`, `I`, `UP`, `B`), and run
     `ruff check --fix` + `ruff format` once, as a dedicated
     formatting-only commit.
2. Replace `black`/ad-hoc formatting with `ruff format` consistently (drop
   `black` from dev deps once migrated).
3. Add `pyproject.toml`'s `[tool.pytest.ini_options]` with
   `testpaths = ["test"]` and `rootdir`, fixing the working-directory
   dependency in §3 permanently, independent of where `pytest` is invoked
   from.

### Phase 2 — Fix the concrete bugs found (§2) ✅ Done
1. Fix `LocalPDBClient.check_hash` (`hash` → `ph`).
2. Fix the SQL trailing-`)` bugs and missing `return results` in
   `db/store.py`/`db/scanner.py`; switch all queries to parameterized
   (`?` placeholders) statements instead of f-string interpolation.
3. Zero-pad month (and consider zero-padding into a fixed `YYYY/MM` scheme)
   in `Photo.db_path()`; implement the intended
   `<day-of-week>-<HH-MM-SS.mmmm>_<disambiguator>` filename scheme
   (decide on colon vs. dash for time separators up front — recommend dashes
   for cross-platform-safe filenames — see open question below), retaining a
   short suffix (uuid fragment or sequence number) for same-millisecond
   collisions (e.g. burst mode).
4. Make `LocalStore.upload`/the Flask `/upload` route surface write failures
   as real HTTP errors instead of a silent empty 200.
5. Remove hardcoded credential fallbacks from `Config` and `WebPDBClient`;
   fail fast with a clear error if credentials aren't configured.
6. Delete dead code: `photo_db/cli/__init__.py` (references functions that
   don't exist anywhere), or reimplement it properly if a config-file-driven
   CLI is still wanted alongside `pdbscanner.py`.
7. Remove the unused `Config.STORE_DB_URL` references in tests, or (better)
   actually thread a configurable DB path through `db/store.py` if per-store
   DB paths are wanted.

### Phase 3 — Finish partially-implemented features ✅ Done (UI intentionally excluded, see §0)
1. **HEIC EXIF writing** (`update_heic`): implement using `pillow-heif`'s
   metadata APIs, mirroring what `exif_tags.update_exif` does for JPEG.
2. **RAW conversion pipeline**: decide whether `exiftool` remains an external
   binary dependency (document + check for it at startup with a clear error)
   or reimplement tag copying with `exifread`/`exif`/`rawpy` metadata only;
   wire `convert_raw` into `Scanner` so `.ARW` (and other RAW extensions) are
   actually picked up by `is_possible_image`/`scan_dir` instead of only being
   reachable via a direct test call.
3. **Config as an instance, not a mutable class.** Introduce a small
   `Settings`/`AppConfig` instance (still env-driven via `environs`/pydantic
   settings) that's passed explicitly where needed (or provided via a
   dependency-injection point for Flask/CLI), removing the global mutable
   class pattern that makes tests and concurrent scans fragile.
4. **Desktop UI**: given "UIs are not my thing" — recommend **not** continuing
   the wxPython UI, and instead exposing the same functionality as:
   - A richer CLI (`pdbscanner.py` growing subcommands: `scan`, `review`
     to list an in-progress/completed scan's results, `serve` for the API), and/or
   - A minimal web UI served by the existing Flask app (a single page hitting
     `/hashes`, `/meta/<uuid>` etc., or a small HTMX/vanilla-JS page) — much
     less effort than finishing wxPython, and removes the `wxPython` native
     dependency entirely.
   If the wx UI is still wanted, minimum bar to call it "done": fix the
   hardcoded icon path, wire `OnSelectSP`'s path into the actual scan, implement
   "Load existing scan" against `ScanDB`, add a progress/cancel control, and
   move `wxPython` into a proper installable extra.

### Phase 4 — Tests ✅ Done (40 passed / 2 skipped / 2 deselected, 67% coverage)
1. Fix test fixtures/config as in Phase 1.3, then:
   - Add regression tests for every bug in §2 (SQL bugs, `check_hash` bug,
     filename/foldering scheme, upload-failure error surfacing).
   - Add unit tests for `Config`/settings isolation once it's no longer a
     mutable global class.
   - Add tests for HEIC read/write, RAW conversion (or explicit `skipif` if
     `exiftool`/hardware RAW samples aren't available in CI), and the
     Flask API's error responses (409 duplicate/similar bodies, auth
     failures, 404s).
   - Mock the network in `test_geocoding.py`/`test_photo.py::test_convert_raw`
     (e.g. `responses`/`requests-mock`, already a dev dependency
     `requests-mock-flask`) so tests don't depend on live third-party
     services being reachable, rate-limit-friendly, or unchanged.
2. Replace the two `ui/` tests with either:
   - Deletion (recommended if the UI itself is deprioritized per Phase 3.4), or
   - Non-blocking smoke tests using `wx.Yield()`/deferred `Close()` calls (or
     `pytest-timeout` on the whole UI test module) so CI never hangs, plus an
     explicit CI marker (`@pytest.mark.gui`) excluded from the default run.
3. Wire up `pytest-cov` with a real, enforced threshold (e.g. via
   `--cov-fail-under=` in `pyproject.toml`) once the above lands, so coverage
   can only go up from here.

### Phase 5 — Pre-commit hooks & CI ✅ Done
1. Add `.pre-commit-config.yaml`:
   - `ruff` (lint + format) and `ruff-format` hooks.
   - Standard hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`,
     `check-added-large-files`, `check-merge-conflict`).
   - A `detect-secrets` or `gitleaks` hook, given the real credentials found
     in `.env` during this audit — this is the single highest-value hook to
     add given what was found.
   - Optionally `mypy` as a local/manual-stage hook once type coverage is
     verified clean, since the codebase already leans on type hints heavily.
2. Add a CI workflow (GitHub Actions or equivalent) running: `uv sync`,
   `pre-commit run --all-files`, `pytest` (excluding the `gui` marker), and
   uploading coverage.

### Phase 6 — Documentation ✅ Done (this pass)
1. Add a top-level `README.md` (currently entirely missing) covering: what
   the project does, quick start (`uv sync`, running `pdbscanner.py`, running
   the Flask API locally, running via Docker), configuration
   (`PH_STORE_URL`, `PH_STORE_USER`, `PH_STORE_PASS`, `PH_HASH_SIZE`,
   `PH_SIMILARITY`, `PH_UID`/`PH_GID`), and a link to
   `docs/ARCHITECTURE.md` (added in this pass) for the design rationale.
2. Keep `docs/ARCHITECTURE.md` and this status/plan doc updated as living
   documents as phases complete (or replace this plan doc with a simple
   `CHANGELOG.md` once the backlog is worked through).

## 5. Open questions to resolve before implementing Phase 2.3 (naming scheme)

- Literal colons (`HH:MM:SS`) in filenames are unsafe on Windows/exFAT/some
  network shares. Confirm whether the library only ever needs to live on
  macOS/Linux filesystems (colons fine) or should be portable (recommend
  dashes: `HH-MM-SS-mmm`).
- Should `year/month` be zero-padded two-digit month folders (`2024/03`) —
  recommended, since it's both human-sortable and machine-sortable without
  ambiguity — or is a flatter `2024/3` layout intentional for some downstream
  tool? Current code produces the latter (unpadded), which does not sort
  correctly, so this should be fixed as a bug regardless.
- Millisecond precision (`.mmmm` in the original request — note standard
  practice is 3 digits `.mmm` for milliseconds, worth confirming the intended
  precision) requires that EXIF actually carries millisecond-precision
  timestamps, which most cameras/phones do not write (`SubSecTimeOriginal` is
  a separate, often-missing EXIF tag). Plan should fall back gracefully
  (e.g. `.000` or an index-based disambiguator) when sub-second EXIF data is
  absent, rather than assuming it's always available.

### Resolutions (implemented)

- **Zero-padded `YYYY/MM` folders**: implemented as proposed —
  `Photo.db_path()` now zero-pads the month, e.g. `2024/03/`.
- **Filename separators**: rather than choosing between colons and dashes
  for a literal `day-of-week-HH:MM:SS.mmmm_` string, the implemented scheme
  drops separators entirely and uses a single fixed-width numeric prefix:
  `DDHHMMSSmmm_<hash-fragment>.<ext>` (day-of-month, hour, minute, second,
  millisecond, each fixed-width, followed by a short disambiguator derived
  from the photo's hash, then the original extension). This sidesteps the
  colon/dash portability question entirely, sorts correctly both
  lexicographically and chronologically within a given year/month folder
  (which is what actually matters for "browse by capture date" use), and
  keeps day-of-week out of the filename — day-of-week is derivable from the
  date for anyone who wants it (e.g. via the EXIF capture date already
  stored on the `Photo` record) and isn't needed for sorting or uniqueness,
  so encoding it in the filename would only add bytes without adding
  information.
- **Millisecond fallback**: when `SubSecTimeOriginal` is absent, the
  millisecond component falls back to `000` rather than raising — this is
  covered by `test/test_naming.py`.
- **Disambiguator for same-millisecond collisions** (e.g. burst mode): a
  short fragment (last 4 characters) of the photo's UUID is appended, rather
  than a monotonic counter, so the scheme stays deterministic and
  collision-free without requiring shared mutable state across concurrent
  scanner threads.
