"""Round-trip test for photo_db.photo.pil_tags.update_heic.

As documented on update_heic() itself: exifread (used by Photo.from_file to
*read* EXIF) cannot parse the HEIC "Exif" box layout produced by
pillow_heif's own encoder - this is a pre-existing exifread/pillow_heif
incompatibility, reproducible even on an untouched, freshly-encoded HEIC
file, and unrelated to update_heic()'s correctness. So this test verifies
the write round-trips correctly using the same pillow_heif + piexif stack
that update_heic() itself uses to write, rather than via Photo.from_file().
"""

from datetime import datetime

import piexif
import pillow_heif
import pytest
from PIL import Image

from photo_db.photo.pil_tags import update_heic

pytest.importorskip("pillow_heif", reason="pillow_heif is required to run/verify HEIC tests")


@pytest.fixture
def blank_heic(tmp_path) -> str:
    path = str(tmp_path / "blank.heic")
    Image.new("RGB", (32, 32), color="red").save(path, format="HEIF", quality=50)
    return path


def _read_back(path: str) -> dict:
    heif_file = pillow_heif.open_heif(path)
    return piexif.load(heif_file.info["exif"])


def test_update_heic_writes_date_camera_and_gps(blank_heic):
    date = datetime(2021, 6, 15, 10, 30, 0)
    update_heic(blank_heic, date=date, camera="Test Camera X100", gps=(51.5074, -0.1278, 35.0))

    exif = _read_back(blank_heic)
    assert exif["0th"][piexif.ImageIFD.Model] == b"Test Camera X100"
    assert exif["Exif"][piexif.ExifIFD.DateTimeOriginal] == b"2021:06:15 10:30:00"
    assert exif["GPS"][piexif.GPSIFD.GPSLatitudeRef] == b"N"
    assert exif["GPS"][piexif.GPSIFD.GPSLongitudeRef] == b"W"


def test_update_heic_southern_western_hemisphere(blank_heic):
    update_heic(blank_heic, gps=(-33.868, -151.209, 12.3))

    exif = _read_back(blank_heic)
    assert exif["GPS"][piexif.GPSIFD.GPSLatitudeRef] == b"S"
    assert exif["GPS"][piexif.GPSIFD.GPSLongitudeRef] == b"W"
    # DMS components must be stored as non-negative magnitudes.
    lat_deg = exif["GPS"][piexif.GPSIFD.GPSLatitude][0]
    assert lat_deg[0] >= 0


def test_update_heic_noop_without_any_fields(blank_heic):
    before = open(blank_heic, "rb").read()
    update_heic(blank_heic)
    after = open(blank_heic, "rb").read()
    assert before == after
