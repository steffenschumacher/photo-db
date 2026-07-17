"""Tests for the Flask routes in photo_db.api.web_store beyond pre_check/upload
(which are already covered indirectly via test_photo.py::test_upload).

Includes a regression test for a real bug: fetch_image() passed a raw
`bytes` object to Flask's send_file(), which requires a path or a
file-like/IO[bytes] object - this crashed with
`AttributeError: 'bytes' object has no attribute 'read'` on every request,
not just in obscure cases.
"""

from hashlib import sha256

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


def test_thumbnail_uses_compact_stable_etag(app, web_client, clean_store, test_config):
    uuid = _upload_sample(web_client)
    photo_hash = web_client.get_meta(uuid).hash

    response = app.test_client().get(
        f"/thumb/{uuid}", auth=(test_config.STORE_USER, test_config.STORE_PASS)
    )

    assert response.status_code == 200
    assert response.content_type == "image/jpeg"
    assert response.get_etag() == (sha256(photo_hash.encode()).hexdigest(), False)
    assert len(response.headers["ETag"]) < 100


def test_get_meta_returns_matching_photo(web_client, clean_store):
    uuid = _upload_sample(web_client)
    meta = web_client.get_meta(uuid)
    assert meta.uuid == uuid
    assert meta.camera == "Apple iPhone 3GS"


def test_hashes_reflects_uploaded_photos(web_client, clean_store):
    uuid = _upload_sample(web_client)
    hashes = web_client.hashes()
    assert uuid in hashes.values()


def test_web_config_exposes_only_browser_algorithm_settings(app, test_config):
    response = app.test_client().get(
        "/web-config", auth=(test_config.STORE_USER, test_config.STORE_PASS)
    )
    assert response.status_code == 200
    assert response.json == {
        "hash_size": test_config.HASH_SIZE,
        "similarity": test_config.SIMILARITY,
    }


def test_rotate_persists_and_reorients_fetched_image(web_client, clean_store):
    uuid = _upload_sample(web_client)
    assert web_client.get_meta(uuid).rotation == 0

    new_rotation = web_client.rotate(uuid, 90)
    assert new_rotation == 90
    assert web_client.get_meta(uuid).rotation == 90

    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        original = f.read()
    from io import BytesIO

    from PIL import Image

    with Image.open(BytesIO(original)) as img:
        original_size = img.size

    rotated_bytes = web_client.get(uuid)
    with Image.open(BytesIO(rotated_bytes)) as img:
        assert img.size == (original_size[1], original_size[0])

    # Rotating again wraps around rather than growing unbounded.
    assert web_client.rotate(uuid, 90) == 180
    assert web_client.rotate(uuid, 270) == 90


def test_rotate_unknown_uuid_returns_not_found(web_client, clean_store):
    import pytest

    with pytest.raises(ValueError):
        web_client.rotate("does-not-exist", 90)
