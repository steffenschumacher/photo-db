import shutil
import subprocess
from io import BytesIO
from os.path import join
from uuid import uuid4

import imageio
import rawpy
from exifread import process_file

from photo_db.config import Config, default_config
from photo_db.photo.photo import LocalPhoto


def _print_exif_tags(tags: dict, debug: bool) -> None:
    if debug:
        for key, value in tags.items():
            print(f"{key}: {value}")


def convert_raw(path: str, config: Config = default_config) -> LocalPhoto:
    local_path = join(config.temp_folder(), f"{uuid4()}.jpeg")
    with open(path, "rb") as image_file:
        buf = BytesIO(image_file.read())
        buf.seek(0)
        tags = process_file(buf)
    _print_exif_tags(tags, config.DEBUG)
    buf.seek(0)
    with rawpy.imread(buf) as raw:
        rgb = raw.postprocess()
    imageio.imsave(local_path, rgb)

    # exiftool copies over the RAW original's EXIF tags (camera/GPS/date)
    # onto the converted JPEG - rawpy's postprocess() doesn't preserve
    # them. It's a separate system binary (not pip-installable), so it may
    # not be present in every environment: degrade gracefully rather than
    # crashing the whole scan over one file - the converted photo will
    # simply be missing EXIF data and get rejected by the caller's usual
    # "incomplete EXIF" handling instead.
    if shutil.which("exiftool"):
        subprocess.Popen(["exiftool", "-TagsFromFile", path, local_path]).wait()
    else:
        print(
            "exiftool not found on PATH - converted RAW photo will be missing "
            "EXIF tags (camera/GPS/date); install exiftool to preserve them"
        )

    ph = LocalPhoto.from_file(local_path, config=config)
    return ph
