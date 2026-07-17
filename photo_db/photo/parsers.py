from base64 import b64decode, b64encode
from datetime import datetime
from io import BytesIO

import numpy as np
from imagehash import ImageHash
from numpy import dtype, frombuffer
from PIL import Image
from pillow_heif import register_heif_opener

from photo_db.config import Config, default_config

register_heif_opener()

#: np.rot90(array, k) rotates counter-clockwise by 90*k degrees; mapping
#: from the *clockwise* degrees convention used everywhere else in this
#: codebase (Photo.rotation, photo_db.photo.orientation) to the `k` that
#: produces that same visual result.
_CW_DEGREES_TO_ROT90_K = {0: 0, 90: 3, 180: 2, 270: 1}


def parse_date(tags: dict[str, object], image_descr: str) -> datetime:
    default_fmt = "%Y:%m:%d %H:%M:%S"
    candidates = {
        "Image DateTime": default_fmt,
        "EXIF DateTimeOriginal": default_fmt,
        "EXIF DateTimeDigitized": default_fmt,
    }
    for tag, fmt in candidates.items():
        if value := tags.get(tag):
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                print(f"{image_descr}: has unexpected datetime format ({value}) in tag {tag}")
    raise ValueError(f"{image_descr}: Unable to parse datetime")


def parse_camera(tags: dict[str, object], image_descr: str) -> str:
    if model := tags.get("Image Model"):
        return f"{tags['Image Make']} {model}"
    return "unknown camera"


def parse_gps(tags: dict[str, object], image_descr: str) -> (float, float, float):
    if "GPS GPSLatitudeRef" not in tags:
        return None, None, None

    results = {}
    try:
        for key in ["Latitude", "Longitude"]:
            multiplier = 1 if tags[f"GPS GPS{key}Ref"].values[0] in ["N", "E"] else -1
            values = tags[f"GPS GPS{key}"].values
            results[key] = multiplier * (
                float(values[0]) + float(values[1]) / 60.0 + float(values[2]) / 3600.0
            )
        if alt := tags.get("GPS GPSAltitude"):
            results["Altitude"] = float(alt.values[0])
        else:
            results["Altitude"] = 0
        return results["Latitude"], results["Longitude"], results["Altitude"]
    except Exception:
        print(f"{image_descr}: has unparsable GPS coordinates")

    raise ValueError(f"{image_descr}: Unable to parse GPS")


def parse_ext_hash_dimensions(
    img_data: BytesIO,
    config: Config = default_config,
) -> (str, dict[int, str], int, int):  # b64 encoded hash variants + dimensions
    with Image.open(img_data) as img:
        img_ext = img.get_format_mimetype().split("/")[-1]
        hash_variants = rotation_hash_variants(img, config.HASH_SIZE)
        return img_ext, hash_variants, img.width, img.height


def rotation_hash_variants(img: Image.Image, hash_size: int) -> dict[int, str]:
    """Compute the average-hash bit-grid for ``img`` at each of the four
    90-degree rotations (clockwise degrees: 0/90/180/270), from a single
    decode+resize.

    Rotating the already-tiny ``hash_size x hash_size`` grid is
    essentially free next to decoding/resizing the original image (the
    mean used for thresholding is rotation-invariant, since rotating is
    just a permutation of the same values), so this makes duplicate
    detection robust to photos physically re-saved/rotated by some other
    tool at negligible extra cost - regardless of what (if anything)
    their EXIF ``Orientation`` tag claims. See ``LocalStore.check_hash``.

    The ``0`` degrees variant is byte-for-byte identical to
    ``imagehash.average_hash(img, hash_size)`` - i.e. today's existing,
    already-persisted ``Photo.hash`` values remain valid/unchanged.
    """
    gray = img.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray)
    avg = pixels.mean()
    variants = {}
    for degrees, k in _CW_DEGREES_TO_ROT90_K.items():
        rotated = np.rot90(pixels, k)
        img_hash = ImageHash(rotated > avg)
        variants[degrees] = b64encode(img_hash.hash.tobytes()).decode("utf-8")
    return variants


def image_hash_from(b64str: str, config: Config = default_config) -> ImageHash:
    raw_bytes = b64decode(b64str)
    one_d = frombuffer(raw_bytes, dtype=dtype(bool))
    two_d = one_d.reshape(config.HASH_SIZE, config.HASH_SIZE)
    return ImageHash(two_d)


def hashes_similar(hash_a: str, hash_b: str, config: Config = default_config) -> bool:
    """Perceptual-similarity check between two b64-encoded hash strings
    directly (rather than via a ``Photo`` instance's own ``_img_hash``),
    so callers can compare arbitrary rotation variants against each
    other - see ``rotation_hash_variants`` and ``LocalStore.check_hash``."""
    a = image_hash_from(hash_a, config).hash
    b = image_hash_from(hash_b, config).hash
    return np.count_nonzero(a != b) <= config.diff_limit()
