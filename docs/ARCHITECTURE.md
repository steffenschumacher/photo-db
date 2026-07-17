# PhotoDB — Architecture & Vision

## Goal

A client/server system for consolidating photos from many sources (phones,
cameras, memory cards) into one deduplicated, chronologically organized photo
library, while doing the expensive work (duplicate detection) **on the client**
so that clearly-duplicate or clearly-inferior images never have to be uploaded.

## Core ideas

1. **Cheap-first duplicate detection.** Before touching image bytes, use
   metadata that's already available (or trivially readable) to reject/accept
   candidates: EXIF capture date/time, camera model, GPS. Only if a photo looks
   "new" is the more expensive step taken.
2. **Perceptual hash of a scaled-down image.** The client computes an
   `average_hash` (via `imagehash`) over a resized version of the photo. This
   hash is small, fast to compute, and — crucially — **deterministic between
   client and server**, so the client can ask the server "have you already got
   something whose hash is this, or close to it?" *before* uploading the full
   image. This also lets the same algorithm catch near-duplicates such as
   re-compressed, resized, or slightly-edited copies of a photo (perceptual
   hashing tolerates small pixel differences, unlike a cryptographic hash of
   the raw bytes).
3. **Similarity, not just equality.** Two hashes are compared with a Hamming
   distance (`numpy` bit-count) against a configurable threshold
   (`Config.SIMILARITY` / `Config.diff_limit()`), so resized/re-encoded/slightly
   modified copies of the same photo are recognized as duplicates, not just
   byte-identical files.
4. **"Preferable" photo wins.** When two photos are near-duplicates, the one
   with the *earlier* capture date wins; if capture dates are identical, the
   one with more pixels (higher resolution) wins (`Photo.preferable_to`).
   This lets a later, better scan of the same photo replace a lower quality
   previously-imported copy — the intent being asserted in code, though see
   `docs/PROJECT_STATUS_AND_PLAN.md` for gaps in how consistently this is
   enforced.
5. **Deterministic, chronological storage layout.** Once a photo is accepted,
   it is stored under `STORE_URL/<year>/<month>/<filename>`, where the
   filename is built from the capture date so that:
   - Files sort chronologically by name within a folder (important since many
     tools/filesystems list directories alphabetically).
   - Filenames are unique even for many photos taken on the same device on the
     same day.

   The **originally intended** naming scheme (per project owner) was:
   `<day-of-week>-<HH:MM:SS.mmmm>_<...>` — i.e. prefixed with the day of the
   week and a millisecond-precision time, so files are both human-scannable
   and collision-resistant. **The current implementation does not match this
   spec** — see the Photo naming section in the status doc.
6. **Server as dumb, authoritative store.** The Flask API
   (`photo_db/api/web_store.py`) exposes `pre_check`, `upload`, `image/<uuid>`,
   `meta/<uuid>`, `hashes` — enough for a remote client to pre-check a hash,
   upload if not duplicate, and enumerate existing hashes for local
   comparison. `LocalStore` (`photo_db/store/logic.py`) implements the same
   logic for a same-machine ("local") store, and `photo_db/db/store.py` is the
   sqlite persistence layer behind both.
7. **Client abstracts local vs. remote.** `AbstractPDBClient` has two
   implementations: `LocalPDBClient` (talks to `LocalStore`/sqlite directly —
   used when the "library" is a local folder) and `WebPDBClient` (talks to the
   Flask API over HTTP with basic auth — used when the library lives on
   another machine). `init_client()` picks the right one based on whether
   `STORE_URL` looks like an `http(s)://` URL or a local path.
8. **Scanner walks a source folder, calling the client.** `Scanner.scan_dir`
   recursively finds candidate image files, and for each one:
   - Parses `Photo` metadata + hash (`Photo.from_file`).
   - Rejects photos missing camera/GPS/date EXIF data.
   - Compares against other photos *already seen in this scan* (in-memory) to
     catch duplicates within the batch being imported.
   - Compares against the *existing* photo library (`central_hashes`,
     pre-fetched once per scan) and only then uploads.
   - Records status (`detected`, `exif`, `duplicate`, `similar`, `uploaded`,
     `rejected`, `ignored`) per file in an in-memory sqlite `ScanDB
     (photo_db/db/scanner.py)` so a scan run can be reviewed/replayed.
9. **Optional desktop UI (wxPython, unfinished).** A `wx`-based UI
   (`photo_db/ui/`) was started to let a non-technical user pick an import
   folder/library and watch a scan progress in a table. This was never
   finished — see status doc.

## Component map

| Concern | Module |
|---|---|
| Photo model, hashing, filename/foldering rules | `photo_db/photo/photo.py`, `photo_db/photo/parsers.py` |
| EXIF/GPS parsing & writing | `photo_db/photo/parsers.py`, `photo_db/photo/exif_tags.py` |
| RAW (`.ARW`) → JPEG conversion | `photo_db/photo/arw_converter.py` |
| HEIC handling (read + write EXIF/GPS) | `photo_db/photo/pil_tags.py` |
| Directory scanning + in-scan/central dedup logic | `photo_db/scanner/scanner.py` |
| Scan-session sqlite log | `photo_db/db/scanner.py` |
| Library sqlite persistence (hash/meta lookup) | `photo_db/db/store.py` |
| Local filesystem-backed store (write photo, folder layout) | `photo_db/store/logic.py` |
| Client abstraction (local vs. remote) | `photo_db/client/*.py` |
| Flask HTTP API (server side of "remote" library) | `photo_db/api/web_store.py`, `photo_db/app.py` |
| Reverse geocoding helper (address → lat/lon, used by tests/tools) | `photo_db/geocoding/nominatim.py` |
| CLI scanner entry point | `pdbscanner.py` |
| Config (instantiable, DI, env-driven defaults) | `photo_db/config.py` |
| Unfinished desktop UI | `photo_db/ui/*` |

## Deployment shape

`Dockerfile` builds an image running `nginx` + `uwsgi` (via `supervisord`) to
serve the Flask API (`manage.py` / `webapi.py`) — i.e. the intended production
topology is: photo library lives on a server machine, exposed over HTTPS with
basic auth, and one or more client machines run `pdbscanner.py` against local
folders (phone backups, camera SD card dumps, etc.), each doing local dedup
work before contacting the server.

See `docs/PROJECT_STATUS_AND_PLAN.md` for a full audit of how complete each of
these pieces is, concrete bugs found, and a prioritized plan to finish the
project, add tests, add pre-commit hooks, and modernize the toolchain.
