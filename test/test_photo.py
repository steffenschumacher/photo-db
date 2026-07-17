from io import BytesIO
from shutil import which

import pytest
from pytest import raises

from photo_db.exceptions import DuplicateException, SimilarException
from photo_db.geocoding.nominatim import get_coords
from photo_db.photo import LocalPhoto, Photo
from photo_db.photo.exif_tags import update_exif

from .conftest import STATIC_DIR, nearly_equals


def test_upload(web_client, clean_store):
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as sampleimg:
        img_data = sampleimg.read()
        ph = Photo.from_file(BytesIO(img_data), "08-190641-4631.jpeg")
        assert web_client.check_hash(ph)
        assert web_client.upload(img_data)
        with raises(DuplicateException):
            web_client.upload(img_data)
    with open(STATIC_DIR / "08-190641-4631-modified.jpeg", "rb") as sampleimg:
        img_data = sampleimg.read()
        with raises(SimilarException):
            web_client.upload(img_data)


def test_update_exif(exif_incomplete_photo):
    gps = 56.152437162521146, 10.204872527070654, 12.3
    update_exif(exif_incomplete_photo, gps=gps)
    ph = Photo.from_file(exif_incomplete_photo)
    assert nearly_equals(ph.latitude, gps[0], 0.005)
    assert nearly_equals(ph.longitude, gps[1], 0.005)
    assert nearly_equals(ph.altitude, gps[2])


@pytest.mark.skipif(which("exiftool") is None, reason="requires the exiftool binary")
@pytest.mark.network
def test_convert_raw(raw_photo):
    pytest.importorskip("rawpy", reason="rawpy (RAW conversion) is an optional dependency")
    from photo_db.photo.arw_converter import convert_raw

    ph = convert_raw(raw_photo)
    print(ph.local_path)
    coords = get_coords("Strandvejen 154A, 8410, Danmark")
    coords = (coords[0], coords[1], coords[2])
    update_exif(ph.local_path, gps=coords)
    updated_ph = LocalPhoto.from_file(ph.local_path)
    assert updated_ph.longitude is not None
