"""Regression tests for GPS parsing/writing.

Covers two real bugs found and fixed during the Python 3.13/pydantic v2
modernization:

1. photo_db.photo.parsers.parse_gps computed a hemisphere sign multiplier
   but the comparison (`tags[...] in ["N", "E"]`) compared an exifread
   IfdTag object directly against strings, which always evaluated False
   (falling back to identity comparison) - so the multiplier was always -1
   internally, and separately was never even applied to the returned value.
   The net effect: every parsed coordinate came out positive, regardless of
   hemisphere.
2. photo_db.photo.exif_tags.dd_to_dms_notation received signed decimal
   degrees but EXIF GPS DMS components must be non-negative magnitudes
   (sign is conveyed only by the separate Ref tag) - passing a negative
   value crashed with OverflowError deep in the `exif`/`plum` library.
"""

from photo_db.photo import Photo
from photo_db.photo.exif_tags import update_exif

from .conftest import STATIC_DIR, nearly_equals


def test_parse_gps_southern_hemisphere_fixture_has_negative_latitude():
    # This fixture was recorded in the southern hemisphere (Christchurch, NZ).
    ph = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    assert ph.latitude < 0
    assert nearly_equals(ph.latitude, -43.538, tolerance=0.01)
    assert ph.longitude > 0
    assert nearly_equals(ph.longitude, 172.6395, tolerance=0.01)


def test_gps_round_trip_southern_western_hemisphere(exif_incomplete_photo):
    # Sydney-ish coordinates: negative latitude (S) and we also flip the
    # longitude sign here (W) purely to exercise both negative-hemisphere
    # branches in the same round trip, since the fixture itself is in the
    # eastern hemisphere.
    gps = (-33.868, -151.209, 12.3)
    update_exif(exif_incomplete_photo, gps=gps)

    ph = Photo.from_file(exif_incomplete_photo)
    assert ph.latitude < 0
    assert ph.longitude < 0
    assert nearly_equals(ph.latitude, gps[0], tolerance=0.005)
    assert nearly_equals(ph.longitude, gps[1], tolerance=0.005)
    assert nearly_equals(ph.altitude, gps[2])


def test_gps_round_trip_northern_eastern_hemisphere(exif_incomplete_photo):
    gps = (56.152437162521146, 10.204872527070654, 12.3)
    update_exif(exif_incomplete_photo, gps=gps)

    ph = Photo.from_file(exif_incomplete_photo)
    assert ph.latitude > 0
    assert ph.longitude > 0
    assert nearly_equals(ph.latitude, gps[0], tolerance=0.005)
    assert nearly_equals(ph.longitude, gps[1], tolerance=0.005)
    assert nearly_equals(ph.altitude, gps[2])
