from io import BytesIO
from shutil import which

import pytest
from pytest import raises

from photo_db.exceptions import DuplicateException, SimilarException
from photo_db.geocoding.nominatim import get_coords
from photo_db.photo import LocalPhoto, Photo
from photo_db.photo.exif_tags import update_exif

from .conftest import STATIC_DIR, nearly_equals


def test_raw_exif_dump_respects_debug_flag(capsys):
    pytest.importorskip("rawpy", reason="rawpy (RAW conversion) is an optional dependency")
    from photo_db.photo.arw_converter import _print_exif_tags

    tags = {"Image Make": "SONY", "EXIF DateTimeOriginal": "2009:08:15 17:51:11"}
    _print_exif_tags(tags, debug=False)
    assert capsys.readouterr().out == ""

    _print_exif_tags(tags, debug=True)
    output = capsys.readouterr().out
    assert "Image Make: SONY" in output
    assert "EXIF DateTimeOriginal: 2009:08:15 17:51:11" in output


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


def test_convert_raw_without_exiftool_binary_raises_valueerror_not_filenotfounderror(
    raw_photo, monkeypatch
):
    """Regression test: convert_raw() used to shell out to exiftool
    unconditionally (subprocess.Popen(["exiftool", ...])), so on any machine
    without that system binary installed (e.g. a plain CI runner) it raised
    an uncaught FileNotFoundError - which Scanner.process_image's except
    clause doesn't catch (only ValueError/ImportError/ModuleNotFoundError),
    crashing the entire scan batch (see test_scanner.py::test_scan and
    Scanner.uploading_complete). Without exiftool the converted photo
    genuinely has no EXIF date to parse, so LocalPhoto.from_file() still
    raises - but now a ValueError, the same already-handled "reject this one
    photo, keep scanning" category as any other incomplete-EXIF photo,
    instead of an unhandled FileNotFoundError."""
    pytest.importorskip("rawpy", reason="rawpy (RAW conversion) is an optional dependency")
    import photo_db.photo.arw_converter as arw_converter

    monkeypatch.setattr(arw_converter.shutil, "which", lambda _: None)
    with pytest.raises(ValueError):
        arw_converter.convert_raw(raw_photo)
