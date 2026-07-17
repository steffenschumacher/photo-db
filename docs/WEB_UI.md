# Angular web companion

The Angular 22 application in `web-ui/` is a same-origin companion to the
desktop client. It loads lean `/sync` metadata into session memory, fetches
authenticated thumbnails only as cards approach the viewport, and opens full
images on demand. Basic Auth credentials are retained only for the browser tab
session. No metadata is retained in IndexedDB or any other browser database;
each refresh and each folder scan starts a new paginated sync from the backend.

Chrome and Edge additionally expose **Scan a folder**. The browser walks the
chosen directory locally, rejects RAW/unsupported files, checks camera/date/GPS
EXIF before image decoding, and calculates the Python-compatible 70×70 average
hash at all four rotations. Candidate hashes are compared with the in-memory
library and earlier files in the same scan. Only selected, unmatched files are
sent to `/upload`. HEIC decoding is loaded lazily through `heic2any`.

## Development

Run Flask on port 5000, then start Angular; `proxy.conf.json` keeps API requests
same-origin during development.

```bash
uv run flask --app photo_db.app:create_app run --port 5000
cd web-ui
npm ci
npm start
npm run e2e
```

## Fixture acceptance check

After uploading `test/static/08-190641-4631.jpeg` and
`test/static/0A4E249E-E8B1-4BA8-8FBD-6D778B3DE99E.heif` through the desktop or
API client, sync the browser library and scan `test/static/`. Both originals
and their copies should report **duplicate**; `25-121007-33d0.jpeg` should
report **incomplete**; and `15175111__DSC04832.ARW` should report **desktop**.
Rotate a JPEG physically (not only via EXIF) and rescan it to validate the
rotation variants.

The Playwright acceptance test automates this flow in real Chromium, including
browser HEIF decode, upload, server-side Pillow hashing, and a second scan that
must recognize the uploaded HEIF as a duplicate.

No additional online HEIC fixture is committed: the samples located during
implementation did not carry sufficiently explicit image-level redistribution
provenance. The repository's existing HEIF fixture already exercises both the
Python decoder and the documented browser acceptance flow.
