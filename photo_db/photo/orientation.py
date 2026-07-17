"""Helpers for reconciling EXIF orientation and user-applied rotation.

Two independent sources of "this image needs turning" have to be
reconciled whenever an image is rendered for display (thumbnail
generation, or serving the full original for the desktop UI's preview
popup):

  1. the EXIF ``Orientation`` tag written by the camera - handled
     automatically via :func:`PIL.ImageOps.exif_transpose`;
  2. a user-applied correction on top of that (e.g. "this still looks
     sideways, rotate it another 90 degrees") - stored as
     ``Photo.rotation`` (clockwise degrees: 0/90/180/270).

Both need to be baked into whatever bytes are actually shown/thumbnailed,
without ever touching the original file on disk - rotation is a display
correction only, the stored original stays byte-for-byte as uploaded.
"""

from io import BytesIO

from PIL import Image, ImageOps

_ORIENTATION_TAG = 0x0112  # "Orientation", see PIL.ExifTags.TAGS


def needs_reorientation(image_bytes: bytes, rotation: int = 0) -> bool:
    """True if rendering ``image_bytes`` would actually change any pixels
    (EXIF orientation other than "normal", or a nonzero manual rotation) -
    lets callers skip a pointless re-encode when there's nothing to do."""
    if rotation % 360 != 0:
        return True
    with Image.open(BytesIO(image_bytes)) as img:
        return img.getexif().get(_ORIENTATION_TAG, 1) != 1


def render_oriented(
    image_bytes: bytes, rotation: int = 0, quality: int = 92
) -> tuple[bytes, str | None]:
    """Return ``(bytes, format)`` of ``image_bytes`` with EXIF
    auto-orientation and an additional clockwise ``rotation`` (degrees)
    applied, for display purposes.

    If nothing needs correcting, returns ``(image_bytes, None)`` unchanged
    (``format=None`` signals "still whatever format it originally was").
    Otherwise the result is always re-encoded as JPEG (``format="jpg"``),
    since the original may be a RAW/HEIC format PIL can decode but not
    necessarily re-encode as-is.
    """
    if not needs_reorientation(image_bytes, rotation):
        return image_bytes, None
    with Image.open(BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        if rotation % 360:
            img = img.rotate(-rotation, expand=True)
        img = img.convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=quality)
        return out.getvalue(), "jpg"


__all__ = ["render_oriented", "needs_reorientation"]
