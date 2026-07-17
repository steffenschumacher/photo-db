from base64 import b64decode, b64encode
from datetime import datetime
from io import BytesIO

from imagehash import ImageHash, average_hash
from numpy import dtype, frombuffer
from PIL import Image
from pillow_heif import register_heif_opener

from photo_db.config import Config

register_heif_opener()


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
) -> (str, str, int, int):  # b64 encoded hash + dimensions
    with Image.open(img_data) as img:
        img_ext = img.get_format_mimetype().split("/")[-1]
        img_hash = average_hash(img, Config.HASH_SIZE)
        str_hash = b64encode(img_hash.hash.tobytes()).decode("utf-8")
        return img_ext, str_hash, img.width, img.height


def image_hash_from(b64str: str) -> ImageHash:
    raw_bytes = b64decode(b64str)
    one_d = frombuffer(raw_bytes, dtype=dtype(bool))
    two_d = one_d.reshape(Config.HASH_SIZE, Config.HASH_SIZE)
    return ImageHash(two_d)
