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


def test_local_store_rotate_regenerates_thumbnail_with_new_orientation(
    local_store_client, clean_store
):
    """Regression test: LocalStore.rotate() must bake the new rotation into
    the regenerated thumbnail, not just the full-size ``get_display_bytes``
    path - otherwise the thumbnail grid keeps showing the old orientation
    after a manual rotate."""
    uuid = local_store_client.upload(_sample_bytes())
    thumb_before = local_store_client.get_thumbnail(uuid)
    with Image.open(BytesIO(thumb_before)) as img:
        size_before = img.size

    local_store_client.rotate(uuid, 90)

    thumb_after = local_store_client.get_thumbnail(uuid)
    with Image.open(BytesIO(thumb_after)) as img:
        size_after = img.size

    assert size_after == (size_before[1], size_before[0])


def test_web_client_fetch_thumbnail(web_client, clean_store):
    uuid = web_client.upload(_sample_bytes())
    thumb = web_client.get_thumbnail(uuid)
    with Image.open(BytesIO(thumb)) as img:
        assert img.format == "JPEG"
        assert img.width * img.height <= 300_000 * 1.2


def test_generate_thumbnail_auto_rotates_per_exif_orientation():
    """25-121007-33d0.jpeg carries EXIF Orientation=6 (rotate 90 CW to
    display correctly) and is physically stored landscape (1600x1200) -
    the thumbnail must come out portrait (width < height) once corrected,
    not just downscaled as-is."""
    with open(STATIC_DIR / "25-121007-33d0.jpeg", "rb") as f:
        original = f.read()
    with Image.open(BytesIO(original)) as img:
        assert img.getexif().get(0x0112) == 6
        assert img.width > img.height  # stored sideways

    thumb = generate_thumbnail(original, target_pixels=50_000)
    with Image.open(BytesIO(thumb)) as img:
        assert img.format == "JPEG"
        assert img.width < img.height  # corrected to portrait


def test_generate_thumbnail_applies_manual_rotation_on_top_of_exif():
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        original = f.read()
    with Image.open(BytesIO(original)) as img:
        original_size = img.size  # landscape, no EXIF orientation

    thumb = generate_thumbnail(original, target_pixels=10_000_000_000, rotation=90)
    with Image.open(BytesIO(thumb)) as img:
        assert img.size == (original_size[1], original_size[0])
