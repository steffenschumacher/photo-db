"""Tests for thumbnail generation, storage, and serving."""

from io import BytesIO

from PIL import Image

from photo_db.photo.thumbnail import generate_thumbnail

from .conftest import STATIC_DIR


def _sample_bytes() -> bytes:
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        return f.read()


def test_generate_thumbnail_reduces_pixel_count():
    original = _sample_bytes()
    with Image.open(BytesIO(original)) as img:
        original_pixels = img.width * img.height

    thumb = generate_thumbnail(original, target_pixels=50_000)
    with Image.open(BytesIO(thumb)) as img:
        thumb_pixels = img.width * img.height
        assert img.format == "JPEG"

    assert thumb_pixels < original_pixels
    # Allow some slack: thumbnail() fits within a box, doesn't hit the
    # target exactly, but should land in the right ballpark.
    assert thumb_pixels <= 50_000 * 1.2


def test_generate_thumbnail_does_not_upscale_small_images():
    original = _sample_bytes()
    with Image.open(BytesIO(original)) as img:
        original_size = img.size

    thumb = generate_thumbnail(original, target_pixels=10_000_000_000)
    with Image.open(BytesIO(thumb)) as img:
        assert img.size == original_size


def test_local_store_generates_thumbnail_on_upload(local_store_client, clean_store):
    uuid = local_store_client.upload(_sample_bytes())
    thumb = local_store_client.get_thumbnail(uuid)
    assert thumb
    with Image.open(BytesIO(thumb)) as img:
        assert img.format == "JPEG"
        assert img.width * img.height <= 300_000 * 1.2


def test_local_store_backfills_missing_thumbnail(local_store_client, clean_store):
    import os

    uuid = local_store_client.upload(_sample_bytes())
    ph = local_store_client.get_meta(uuid)
    thumb_path = local_store_client.store.thumb_path(ph)
    os.remove(thumb_path)
    assert not os.path.exists(thumb_path)

    thumb = local_store_client.get_thumbnail(uuid)
    assert thumb
    assert os.path.exists(thumb_path)


def test_web_client_fetch_thumbnail(web_client, clean_store):
    uuid = web_client.upload(_sample_bytes())
    thumb = web_client.get_thumbnail(uuid)
    with Image.open(BytesIO(thumb)) as img:
        assert img.format == "JPEG"
        assert img.width * img.height <= 300_000 * 1.2
