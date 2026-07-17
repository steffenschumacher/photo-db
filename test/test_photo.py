from datetime import datetime

from pytest import raises
from io import BytesIO
from .conftest import nearly_equals
from photo_db.photo import Photo, LocalPhoto
from photo_db.photo.exif_tags import update_exif
from photo_db.photo.arw_converter import convert_raw
from photo_db.api import DuplicateException, SimilarException
from photo_db.geocoding.nominatim import get_coords


def test_upload(web_client, clean_store):
    with open("static/08-190641-4631.jpeg", "rb") as sampleimg:
        img_data = sampleimg.read()
        ph = Photo.from_file(BytesIO(img_data), "08-190641-4631.jpeg")
        assert web_client.check_hash(ph)
        assert web_client.upload(img_data)
        with raises(DuplicateException):
            web_client.upload(img_data)
    with open("static/08-190641-4631-modified.jpeg", "rb") as sampleimg:
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


def test_convert_raw(raw_photo):
    ph = convert_raw(raw_photo)
    print(ph.local_path)
    coords = get_coords("Strandvejen 154A, 8410, Danmark")
    address = coords[3]
    coords = (coords[0], coords[1], coords[2])
    update_exif(ph.local_path, gps=coords)
    updated_ph = LocalPhoto.from_file(ph.local_path)
    assert updated_ph.longitude is not None
