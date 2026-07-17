"""Thumbnail generation for stored photos.

Thumbnails are generated once, at upload time, and cached to disk (see
``photo_db.store.logic.LocalStore``) so the read path (serving thumbnails to
the thick client for browsing) stays fast and doesn't need to touch the full
original image.
"""

from io import BytesIO

import pillow_heif
from PIL import Image

from .orientation import render_oriented

pillow_heif.register_heif_opener()

#: Target thumbnail size in pixels (width * height). ~300k px is enough
#: detail for browsing a grid of photos while staying small/fast to decode.
DEFAULT_TARGET_PIXELS = 300_000
DEFAULT_QUALITY = 85


def generate_thumbnail(
    image_bytes: bytes,
    target_pixels: int = DEFAULT_TARGET_PIXELS,
    quality: int = DEFAULT_QUALITY,
    rotation: int = 0,
) -> bytes:
    """Generate a JPEG thumbnail of ``image_bytes`` sized to approximately
    ``target_pixels`` total pixels, preserving aspect ratio. Never upscales
    an already-smaller image.

    Auto-rotates according to the source's EXIF orientation tag (if any),
    plus an additional clockwise ``rotation`` (degrees) the user may have
    applied on top of that - see ``photo_db.photo.orientation``.
    """
    image_bytes, _fmt = render_oriented(image_bytes, rotation)
    with Image.open(BytesIO(image_bytes)) as img:
        img = img.convert("RGB")
        width, height = img.size
        current_pixels = width * height
        if current_pixels > target_pixels:
            scale = (target_pixels / current_pixels) ** 0.5
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            img.thumbnail(new_size, Image.LANCZOS)
        out = BytesIO()
        img.save(out, format="JPEG", quality=quality)
        return out.getvalue()


__all__ = ["generate_thumbnail", "DEFAULT_TARGET_PIXELS"]
