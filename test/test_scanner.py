import tempfile
from importlib.util import find_spec

from photo_db.config import Config
from photo_db.db.lean_cache import LeanCache
from photo_db.scanner import Scanner
from photo_db.scanner.scanner import Scanner as ScannerClass

from .conftest import STATIC_DIR


def _bare_scanner() -> ScannerClass:
    # Bypass __init__ (which needs a real client/thread pool) since
    # is_possible_image() is a pure function of the filename.
    return ScannerClass.__new__(ScannerClass)


def _fresh_lean_cache() -> LeanCache:
    # test_config's lean_cache_path is session-scoped/shared - tests that
    # drive a real Scanner need their own throwaway cache, or hash entries
    # from an earlier test's (now clean_store-wiped) uploads would still
    # look like "known" central photos here, and the "similar to a stale
    # uuid" cross-talk would then also crash on the now-missing metadata.
    return LeanCache(Config(lean_cache_path=tempfile.mktemp(suffix=".db")))


def test_is_possible_image_recognizes_supported_extensions(tmp_path):
    sc = _bare_scanner()
    for name in ["photo.jpg", "PHOTO.JPG", "photo.jpeg", "photo.heic", "photo.heif", "photo.arw"]:
        p = tmp_path / name
        p.write_bytes(b"fake image bytes")
        assert sc.is_possible_image(str(p)), f"{name} should be considered a possible image"


def test_is_possible_image_ignores_unsupported_extensions(tmp_path):
    sc = _bare_scanner()
    for name in ["clip.mov", "clip.mp4", "screenshot.png", "notes.txt"]:
        p = tmp_path / name
        p.write_bytes(b"not an image")
        assert not sc.is_possible_image(str(p)), f"{name} should be ignored"


def test_is_possible_image_ignores_missing_and_appledouble_files(tmp_path):
    sc = _bare_scanner()
    assert not sc.is_possible_image(str(tmp_path / "does-not-exist.jpg"))

    apple_double = tmp_path / "._photo.AppleDouble.jpg"
    apple_double.write_bytes(b"resource fork junk")
    assert not sc.is_possible_image(str(apple_double))


def test_scan(local_store_client, clean_store, test_config):
    sc = Scanner(local_store_client, config=test_config, lean_cache=_fresh_lean_cache())

    folder = str(STATIC_DIR)
    sc.scan_dir(folder)
    sc.uploading_complete(blocking=True)

    processed = sc.processed_photos()
    # processed_photos() reports every attempted photo (successful or not),
    # since Scanner records the outcome of every scanned file.
    assert sc.detected > 0
    assert len(processed) == sc.detected
    uploaded = [p for p in sc.scan_hashes.values() if p.status == "uploaded"]
    # 08-190641-4631.jpeg, its near-identical "-modified" variant, the HEIF
    # fixture, and 25-121007-33d0.jpeg (has camera+date but no GPS - GPS is
    # not required for upload eligibility, see process_image()) all end up
    # "uploaded". The ARW fixture does too when both rawpy and exiftool are
    # installed (as they are in CI); otherwise it is reported as ignored.
    # True byte-identical duplicates (sub/, sub2/) are correctly rejected.
    # Note: photo_db/scanner/scanner.py has a pre-existing (not
    # modified here) quirk where a "preferable" near-duplicate is still
    # uploaded alongside the original rather than replacing it - flagged as
    # a follow-up, not fixed in this pass to avoid changing scan behavior
    # beyond what was requested.
    from importlib.util import find_spec
    from shutil import which

    raw_available = (
        find_spec("rawpy") is not None
        and find_spec("imageio") is not None
        and which("exiftool") is not None
    )
    assert len(uploaded) == (5 if raw_available else 4)


def test_process_image_uploads_photo_missing_only_gps(local_store_client, clean_store, test_config):
    """25-121007-33d0.jpeg has valid camera+date EXIF but no GPS - GPS is
    deliberately optional (see process_image()), so it should upload
    normally rather than being rejected as "incomplete EXIF"."""
    sc = Scanner(local_store_client, config=test_config, lean_cache=_fresh_lean_cache())
    ph = sc.process_image(str(STATIC_DIR), "25-121007-33d0.jpeg")
    assert ph.status == "uploaded"
    assert ph.reject_reason is None


def test_process_image_ignores_photo_missing_camera_and_date(
    local_store_client, clean_store, test_config, tmp_path
):
    """Camera and capture date are non-optional fields on Photo (unlike
    GPS), so a file with neither can never become a valid Photo in the
    first place - LocalPhoto.from_file() raises ValueError, which
    process_image() reports as status "ignored" rather than "exif" (that
    status is now GPS-only-completeness territory, and GPS alone never
    blocks upload)."""
    from PIL import Image

    bare = tmp_path / "no_exif.jpeg"
    Image.new("RGB", (32, 32), color="red").save(bare, "JPEG")

    sc = Scanner(local_store_client, config=test_config, lean_cache=_fresh_lean_cache())
    ph = sc.process_image(str(tmp_path), "no_exif.jpeg")
    assert ph.status == "ignored"
    assert "Unable to parse datetime" in ph.reject_reason


def test_scan_from_a_different_thread_than_construction(
    local_store_client, clean_store, test_config
):
    """Regression test for the desktop UI's threading pattern: ScanDialog
    builds a Scanner on the GUI thread, but a QThread worker actually
    drives scan_dir()/uploading_complete() - both ScanDB and LeanCache must
    tolerate that (sqlite connections aren't cross-thread safe by default)."""
    from threading import Thread

    sc = Scanner(local_store_client, config=test_config, lean_cache=_fresh_lean_cache())
    folder = str(STATIC_DIR)
    errors = []

    def _drive():
        try:
            sc.scan_dir(folder)
            sc.uploading_complete(blocking=True)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t = Thread(target=_drive)
    t.start()
    t.join(timeout=30)

    assert not errors, f"scan driven from a worker thread raised: {errors}"
    assert sc.processed == sc.detected


def test_uploading_complete_skips_a_failed_future_instead_of_aborting_the_batch(
    local_store_client, clean_store, test_config
):
    """Regression test: uploading_complete() used to treat any unexpected
    exception raised while resolving a future as fatal to the whole drain
    loop (`return False, photos` without processing the remaining futures),
    even when called with blocking=True (which callers reasonably expect to
    fully drain self.futures in one call). One bad file (e.g. a RAW photo
    hitting a missing exiftool binary) would silently strand the rest of an
    otherwise-healthy batch. Now a single failed future is logged and
    skipped, and the remaining futures are still processed."""
    sc = Scanner(local_store_client, config=test_config, lean_cache=_fresh_lean_cache())

    def _boom():
        raise RuntimeError("simulated unexpected processing failure")

    def _ok():
        from datetime import datetime
        from uuid import uuid4

        from photo_db.photo.photo import LocalPhoto

        return LocalPhoto(
            path="/tmp/does-not-matter.jpeg",
            camera="Unknown",
            date=datetime.now(),
            width=1,
            height=1,
            hash=str(uuid4()),
            extension="jpeg",
            status="ignored",
        )

    sc.futures.appendleft(sc.pool.submit(_boom))
    sc.futures.appendleft(sc.pool.submit(_ok))
    sc.futures.appendleft(sc.pool.submit(_ok))
    sc.detected = 3

    done, photos = sc.uploading_complete(blocking=True)

    assert done
    # Both non-failing futures must still be drained (and upserted) despite
    # the failed one sitting among them - not stranded behind it.
    assert len(photos) == 2
    assert sc.processed == 3
