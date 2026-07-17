"""Tests for the Flask routes in photo_db.api.web_store beyond pre_check/upload
(which are already covered indirectly via test_photo.py::test_upload).

Includes a regression test for a real bug: fetch_image() passed a raw
`bytes` object to Flask's send_file(), which requires a path or a
file-like/IO[bytes] object - this crashed with
`AttributeError: 'bytes' object has no attribute 'read'` on every request,
not just in obscure cases.
"""

from .conftest import STATIC_DIR


def _upload_sample(web_client) -> str:
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        img_data = f.read()
    return web_client.upload(img_data)


def test_fetch_image_round_trips_bytes(web_client, clean_store):
    uuid = _upload_sample(web_client)
    fetched = web_client.get(uuid)

    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        original = f.read()
    assert fetched == original


def test_get_meta_returns_matching_photo(web_client, clean_store):
    uuid = _upload_sample(web_client)
    meta = web_client.get_meta(uuid)
    assert meta.uuid == uuid
    assert meta.camera == "Apple iPhone 3GS"


def test_hashes_reflects_uploaded_photos(web_client, clean_store):
    uuid = _upload_sample(web_client)
    hashes = web_client.hashes()
    assert uuid in hashes.values()
