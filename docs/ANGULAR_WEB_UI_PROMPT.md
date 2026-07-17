# Prompt: Angular web companion for PhotoDB

> **Status:** not started. This document is a self-contained implementation
> prompt/spec for a future session (human or agent) to pick up — it is not
> itself an implementation plan that's been executed. Nothing in
> `photo_db/`, the repo's git history, or its other docs references an
> Angular/JS/WASM frontend before this file; the only prior trace is a
> throwaway one-line suggestion in `docs/PROJECT_STATUS_AND_PLAN.md`
> ("a minimal web UI... much less effort than finishing wxPython"), which
> was superseded by the PySide6 desktop thick client that actually got
> built instead.

## Goal

Build a browser-based **companion** to the existing PySide6 desktop thick
client (`photodb-ui.py`) — not a replacement. The desktop app remains the
primary tool for curating/reorganizing a local photo library (including RAW
handling, which is out of scope for the web app - see "Non-goals"). The web
app's job:

1. **Browse the remote library** from any machine with a browser, no install
   required: lazily-loaded thumbnail grid, filterable/browsable by date
   range, full-image preview.
2. **Scan a local folder** (via the browser, no server round-trip for the
   scan itself) and determine, using the *same* client-side duplicate
   detection logic as the desktop app, which local files are already in the
   remote library vs. genuinely new — then let the user trigger uploads for
   the new ones directly from the browser.

This mirrors the project's core "cheap-first, client-side duplicate
detection" philosophy (see `docs/ARCHITECTURE.md`) — the point is to avoid
uploading/transferring full-resolution images just to find out they're
already in the store, whether that logic runs in Python (desktop) or
TypeScript (browser).

## Non-goals for v1 (explicitly out of scope)

- **RAW file support** (`.ARW` etc.). No practical in-browser decode path
  exists without a heavy WASM port of something like LibRaw. If a scanned
  folder contains RAW files, flag them in the UI as "needs the desktop
  client" rather than attempting to process them.
- **Local file reorganization** (renaming into `year/month/<prefix>_...`
  folder structure, as the desktop/CLI scanners do on adoption). The web
  app's job is *decide and upload*, not manage the local folder structure -
  leave that to the desktop app / `pdbscanner.py`.
- **Manual rotation editing UI** (the desktop app's "rotate and persist back
  to the store" popup) - v1 is read/browse + scan/upload only. Could be a v2
  addition once the read paths are solid, reusing the existing `/rotate/<uuid>`
  endpoint.
- Cross-browser parity for local folder scanning: **Chromium-only for v1**
  (File System Access API - see below). Firefox/Safari can still use the
  "browse remote library" half of the app; local scanning should
  feature-detect and show a clear "use Chrome/Edge" message otherwise.

## Prior art to reuse conceptually (read before starting)

- `docs/ARCHITECTURE.md` - the overall design philosophy (cheap-first
  checks, perceptual hashing, rotation-invariant hash variants,
  "preferable photo wins").
- `photo_db/scanner/scanner.py` (`Scanner.process_image`,
  `check_with_processed_photos`, `check_with_central_photos`) - the exact
  order of checks the desktop/CLI scanners perform; the web app's
  client-side check flow should mirror this (cheap EXIF-completeness
  check first, then hash comparison, only upload if nothing local/remote
  matches).
- `photo_db/db/lean_cache.py` + `photo_db/client/local_client.py`
  (`LeanCache`) - the desktop app's local sqlite cache of remote metadata,
  synced incrementally via `/sync`. The web app needs a browser-side
  equivalent (IndexedDB) serving the same purpose.
- `photo_db/ui/thumbnail_loader.py` / `thumbnail_model.py` /
  `thumbnail_grid.py` - the desktop app's lazy-loading thumbnail grid
  pattern (load metadata for a date range, fetch thumbnails on demand,
  cache them client-side) - the Angular grid component should follow the
  same UX shape.
- `photo_db/photo/parsers.py` (`rotation_hash_variants`,
  `hashes_similar`) - the **exact perceptual-hash algorithm** to reimplement
  in TypeScript (see below - this is the trickiest/most safety-critical
  part to get bit-compatible).

## Backend API surface already available (`photo_db/api/web_store.py`)

All routes require HTTP Basic Auth (`flask_httpauth`, `@auth.login_required`)
against `Config.STORE_USER`/`STORE_PASS`. No CORS is currently configured.

| Route | Method | Purpose |
|---|---|---|
| `/pre_check` | POST | Body: a `Photo` JSON payload (including `hash`). Raises 409 (`DuplicateException`/`SimilarException`, JSON body) if the store already considers it a duplicate/near-duplicate. |
| `/upload` | POST | Body: raw image bytes. Stores the image (extracts its own metadata server-side); same 409 semantics as `/pre_check` on conflict. |
| `/image/<uuid>` | GET | Full display-resolution image bytes (EXIF/rotation-corrected), for the preview popup. |
| `/thumb/<uuid>` | GET | ~300k-pixel thumbnail JPEG (rotation-corrected), `ETag` set to the photo's hash for client-side caching. |
| `/meta/<uuid>` | GET | Full `Photo` metadata as JSON (dates as unix timestamps). |
| `/rotate/<uuid>` | POST | Body: `{"delta": 90}` (or 180/270/-90). Persists a manual rotation correction. (v2 scope, see Non-goals.) |
| `/hashes` | GET | `{hash: uuid}` map of every photo currently in the store - the simplest (if coarse) "is this hash known?" check. |
| `/sync` | GET | `?since=<unix ts>&limit=<n>` - incremental **lean** metadata sync: `{"photos": [Photo.lean_dict(), ...], "next_since": <ts>}`. This is what the web app should use to build its local IndexedDB cache (mirrors `LeanCache`), not repeatedly hitting `/hashes` for everything. |

`Photo.lean_dict()` shape (see `photo_db/photo/photo.py`):
```json
{
  "uuid": "...", "hash": "<base64 avg-hash, 0deg variant>",
  "date": 1699999999.0, "width": 4032, "height": 3024,
  "camera": "Apple iPhone 12 mini",
  "latitude": 56.15, "longitude": 10.20,
  "extension": "jpeg", "scanned": 1699999999.0
}
```

### Backend changes almost certainly needed before the web app can work

1. **CORS**, unless the Angular build is served *from* the same Flask app
   as a static bundle (simplest option - avoids CORS and auth-cookie/header
   complications entirely; recommend this for v1 rather than a separately
   hosted SPA). If serving separately is preferred instead, add
   `flask-cors` scoped to the specific origin(s).
2. **Auth for a browser context.** HTTP Basic Auth works via `fetch()` with
   an `Authorization: Basic ...` header, but there's no login form/session
   today - decide whether v1 just prompts once client-side and stores the
   credential (e.g. in memory + `sessionStorage`, never `localStorage`) for
   the session, or whether it's worth adding a minimal session/token auth
   layer to the backend. Recommend starting with the simple stored-Basic-Auth
   approach and revisiting if this becomes a real product, not just a
   personal tool.
3. Confirm `/sync`'s `limit` default (5000) and pagination behavior are
   sufficient for a library of your actual size, or whether the web client
   needs to loop calls until `next_since` stops advancing.

## The perceptual hash: byte-for-byte compatibility is mandatory

This is the part most likely to go subtly wrong, so it gets its own section.
The server-side algorithm (`rotation_hash_variants` in
`photo_db/photo/parsers.py`) is:

1. Decode the image, convert to **grayscale** (`Image.convert("L")`).
2. **Resize to `hash_size x hash_size`** (config `PH_HASH_SIZE`, default
   **70** - i.e. a 70x70 grid, *not* the traditional imagehash default of 8)
   using **Lanczos** resampling (`Image.Resampling.LANCZOS`).
3. Compute the **mean** pixel value of that resized grid.
4. Produce a boolean grid: `pixel > mean` for every cell.
5. For duplicate-detection robustness against physically-rotated re-saves,
   also compute this same boolean grid rotated 90/180/270 degrees
   (`np.rot90`) - rotating the mean-thresholded grid is equivalent to
   thresholding a rotated resize, since the mean is rotation-invariant.
6. Encode: **one byte per grid cell** (`0x00`/`0x01`, *not* bit-packed -
   verified empirically: `numpy` bool array `.tobytes()` gives one byte per
   element), row-major, then **base64**.
7. Similarity comparison (`hashes_similar`): base64-decode both hashes back
   to `hash_size x hash_size` boolean grids, count differing cells
   (Hamming distance), compare against `diff_limit()` =
   `floor((1 - SIMILARITY/100) * hash_size^2)` (config `PH_SIMILARITY`,
   default **97**, i.e. up to ~3% of cells may differ and still count as
   "the same photo").

**TypeScript implementation approach:**
- Decode/resize via `<canvas>` (`drawImage` with the target 70x70 size,
  `imageSmoothingQuality: "high"` is the closest browser equivalent to
  Lanczos, but is not guaranteed pixel-identical to Pillow's LANCZOS
  kernel - **this is the main risk**: near-duplicate/rotation detection
  needs the same photo to hash similarly whether processed by the desktop
  client or the browser, but does *not* need bit-for-bit identical hash
  strings between the two (the similarity comparison already tolerates
  ~3% difference). Validate this empirically (see Acceptance Criteria)
  rather than assuming it'll just work.
- Grayscale via the standard luminance formula on canvas pixel data
  (`ImageData`), matching Pillow's `"L"` conversion (ITU-R 601-2 luma
  transform: `0.299R + 0.587G + 0.114B`).
- Compute mean, threshold, rotate the 70x70 boolean grid (trivial in JS -
  same `np.rot90`-equivalent index remapping).
- Encode exactly as the backend does (one byte per cell, base64) so hashes
  computed in the browser are directly comparable to hashes fetched from
  `/sync`/`/hashes` with zero server-side translation needed.
- Implement `hashSimilar(a, b, hashSize, similarity)` mirroring
  `hashes_similar`/`diff_limit` exactly (same formula, same floor/threshold
  semantics) so the "is this a duplicate" verdict matches the backend's
  verdict for the same pair of hashes.

No WASM needed for this - it's small-grid pixel math, well within plain
JS/TS performance budgets even for a few thousand comparisons client-side.

## EXIF/metadata parsing

Use `exifr` (mature, pure-JS, handles JPEG/TIFF/HEIC containers) to extract:
capture date/time, camera make/model, GPS lat/long/altitude - mirroring
`photo_db/photo/parsers.py`'s `parse_date`/`parse_gps`/camera-tag logic
closely enough that the same "reject if incomplete EXIF" cheap-first check
(`Scanner.process_image`'s early-reject branch) can run client-side before
ever computing a hash.

## HEIC handling

Browsers other than Safari can't decode HEIC into a `<canvas>` natively.
Use a WASM HEIC decoder (`libheif-js` or similar) specifically for this file
type - this is the one place WASM earns its complexity budget in this
project. Decode to RGB, then feed into the same canvas-based
resize/grayscale/hash pipeline as any other format.

## Local folder scanning

Use the **File System Access API** (`window.showDirectoryPicker()`,
Chromium-only) to let the user pick a local folder, then recursively walk
it (`FileSystemDirectoryHandle.values()` / `.getFile()`) without uploading
anything just to look at it. For each candidate image file:

1. Cheap check first: parse EXIF, reject early (mirroring
   `Scanner.process_image`) if camera/GPS/date are missing - flag as
   "incomplete metadata" in the UI, don't bother hashing.
2. Compute the perceptual hash (all 4 rotation variants, matching
   `rotation_hash_variants`).
3. Compare against the local IndexedDB cache (synced from `/sync`) using
   `hashSimilar` - if a match is found, mark "already in library" (with a
   link/preview of the matching remote photo via `/thumb/<uuid>`).
4. If no match, mark "new - eligible to upload" and let the user
   batch-select and upload these via `/upload` (raw bytes POST, same
   contract `WebPDBClient.upload` already uses).
5. Files that don't parse as images, or are RAW/unsupported: surface
   clearly as "skipped - needs desktop client" rather than silently
   dropping them.

## Suggested architecture

- **Angular** (per your original vision) + TypeScript, standalone
  components (no need for NgModules in a modern Angular app), Angular
  Signals for state where it fits naturally.
- A dedicated `PerceptualHashService` and `LeanCacheService` (wrapping
  IndexedDB, e.g. via `idb` npm package) as the TS-side equivalents of
  `photo_db/photo/parsers.py` and `photo_db/db/lean_cache.py` respectively
  - keep these framework-agnostic/pure so their hash-compatibility can be
  unit-tested in isolation from Angular's rendering layer.
- A thumbnail grid component mirroring the desktop app's lazy-loading
  approach: virtual-scrolling (e.g. Angular CDK's `ScrollingModule`) over a
  date-sorted list, fetching `/thumb/<uuid>` only for currently-visible
  rows.
- Serve the built Angular bundle from the existing Flask app (a static
  folder + catch-all route) rather than standing up a separate web server -
  simplest deployment story, avoids CORS, and fits the existing
  Docker/Cloudflare Tunnel setup already in place (see
  `docs/ARCHITECTURE.md`'s "Deployment shape" section) with no new
  infrastructure.

## Suggested phased delivery

1. **Phase 1 - read-only browse.** Angular app, served statically by
   Flask, Basic-Auth prompt, `/sync`-backed IndexedDB cache, lazy
   thumbnail grid, full-image preview popup. No local scanning yet - this
   phase alone is independently useful and low-risk.
2. **Phase 2 - perceptual hash port + acceptance testing.** Implement
   `PerceptualHashService`, validate byte-compatibility/similarity-verdict
   parity against the Python implementation (see Acceptance Criteria)
   before building any UI around it.
3. **Phase 3 - local folder scanning + upload.** File System Access API
   integration, the cheap-first EXIF check, hash-based dedup against the
   IndexedDB cache, HEIC WASM decoder, batch upload flow, "needs desktop
   client" flags for RAW/unsupported files.
4. **Phase 4 (optional/v2)** - rotation editing UI reusing `/rotate/<uuid>`.

## Acceptance criteria

- For a representative sample of existing photos in the real store
  (several cameras/phones, at least one HEIC, at least one manually-rotated
  photo), confirm: `hashSimilar(browserHash, pythonHash)` returns `true`
  for the *same* photo processed by both the browser pipeline and
  `rotation_hash_variants` - i.e. the TS reimplementation doesn't need to
  produce byte-identical hashes, but must agree on "is this the same
  photo" with the existing Python implementation, for real images, not
  just synthetic test fixtures.
- Local scanning correctly identifies: (a) an exact duplicate of an
  already-uploaded photo, (b) a physically-rotated re-save of one, (c) a
  genuinely new photo, (d) a photo with incomplete EXIF (rejected before
  hashing, matching `Scanner`'s behavior), (e) a RAW file (flagged as
  "needs desktop client", not silently skipped or crashed on).
- Upload flow round-trips through the real `/upload` endpoint and the
  uploaded photo is then correctly retrievable via the desktop app too
  (proving format/store compatibility, not just "the web app is internally
  consistent").
