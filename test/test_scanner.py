from photo_db.scanner import Scanner
from photo_db.scanner.scanner import Scanner as ScannerClass

from .conftest import STATIC_DIR


def _bare_scanner() -> ScannerClass:
    # Bypass __init__ (which needs a real client/thread pool) since
    # is_possible_image() is a pure function of the filename.
    return ScannerClass.__new__(ScannerClass)


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
    sc = Scanner(local_store_client, config=test_config)

    folder = str(STATIC_DIR)
    sc.scan_dir(folder)
    sc.uploading_complete(blocking=True)

    processed = sc.processed_photos()
    # processed_photos() reports every attempted photo (successful or not),
    # since Scanner records the outcome of every scanned file.
    assert sc.detected > 0
    assert len(processed) == sc.detected
    uploaded = [p for p in sc.scan_hashes.values() if p.status == "uploaded"]
    # 08-190641-4631.jpeg, its near-identical "-modified" variant, and the
    # HEIF fixture all end up "uploaded": true byte-identical duplicates
    # (sub/, sub2/) are correctly rejected, and photos missing GPS/EXIF data
    # are rejected too. Note: photo_db/scanner/scanner.py has a pre-existing
    # (not modified here) quirk where a "preferable" near-duplicate is still
    # uploaded alongside the original rather than replacing it - flagged as
    # a follow-up, not fixed in this pass to avoid changing scan behavior
    # beyond what was requested.
    assert len(uploaded) == 3
