"""Tests for rotation-invariant duplicate detection.

A photo that's the same content but physically re-saved/rotated by some
other tool (e.g. a photo viewer that bakes in a rotation and resets EXIF
Orientation to "normal") should still be recognized as a duplicate of
what's already in the store - not silently adopted as a new, unrelated
photo - and the existing library entry's ``rotation`` should be corrected
so it displays the right way up. See ``LocalStore.check_hash``.
"""

from io import BytesIO

import pytest
from PIL import Image

from photo_db.exceptions import DuplicateException, SimilarException
from photo_db.photo import Photo

from .conftest import STATIC_DIR


def _rotated_bytes(filename: str, degrees: int) -> bytes:
    """Simulate a tool that physically bakes in a rotation (rather than
    just flipping an EXIF tag) and re-saves as JPEG, preserving the
    original's other EXIF data (date/camera/GPS)."""
    with open(STATIC_DIR / filename, "rb") as f:
        original = f.read()
    with Image.open(BytesIO(original)) as img:
        exif = img.info.get("exif")
        rotated = img.convert("RGB").rotate(-degrees, expand=True)
        out = BytesIO()
        rotated.save(out, format="JPEG", quality=95, exif=exif)
        return out.getvalue()


def test_hash_variants_includes_canonical_and_three_rotations():
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        original = f.read()
    ph = Photo.from_file(BytesIO(original), "sample.jpeg")

    variants = ph.hash_variants()
    assert set(variants.keys()) == {0, 90, 180, 270}
    assert variants[0] == ph.hash
    # Rotated variants must actually differ from the canonical hash for a
    # non-symmetric photo, or the test wouldn't be exercising anything.
    assert len({variants[0], variants[90], variants[180], variants[270]}) > 1


def test_photo_loaded_from_store_falls_back_to_canonical_hash_only():
    with open(STATIC_DIR / "08-190641-4631.jpeg", "rb") as f:
        original = f.read()
    ph = Photo.from_file(BytesIO(original), "sample.jpeg")
    # Simulate a Photo reconstructed from DB rows (no source bytes at hand).
    reloaded = Photo(**{k: getattr(ph, k) for k in type(ph).model_fields})
    assert reloaded.hash_variants() == {0: reloaded.hash}


@pytest.mark.parametrize("degrees", [90, 180, 270])
def test_physically_rotated_duplicate_is_rejected_and_rotation_auto_corrected(
    local_store_client, clean_store, degrees
):
    original_bytes = (STATIC_DIR / "08-190641-4631.jpeg").read_bytes()
    with Image.open(BytesIO(original_bytes)) as img:
        original_size = img.size

    uuid = local_store_client.upload(original_bytes)
    assert local_store_client.get_meta(uuid).rotation == 0

    rotated_candidate = _rotated_bytes("08-190641-4631.jpeg", degrees)

    with pytest.raises((DuplicateException, SimilarException)) as excinfo:
        local_store_client.upload(rotated_candidate)
    assert excinfo.value.uuid == uuid

    # The candidate must not have been adopted as a second library entry.
    assert set(local_store_client.hashes().values()) == {uuid}

    meta = local_store_client.get_meta(uuid)
    assert meta.rotation != 0

    # Displaying the existing (corrected) photo should now match the
    # rotated candidate's physical dimensions.
    with Image.open(BytesIO(local_store_client.get(uuid))) as img:
        if degrees in (90, 270):
            assert img.size == (original_size[1], original_size[0])
        else:
            assert img.size == original_size


def test_rotation_correction_does_not_clobber_manual_rotation(local_store_client, clean_store):
    uuid = local_store_client.upload((STATIC_DIR / "08-190641-4631.jpeg").read_bytes())
    local_store_client.rotate(uuid, 90)
    assert local_store_client.get_meta(uuid).rotation == 90

    rotated_candidate = _rotated_bytes("08-190641-4631.jpeg", 180)
    with pytest.raises((DuplicateException, SimilarException)):
        local_store_client.upload(rotated_candidate)

    # A manual correction someone already made should never be silently
    # overwritten by an automatic guess from a later duplicate scan.
    assert local_store_client.get_meta(uuid).rotation == 90
