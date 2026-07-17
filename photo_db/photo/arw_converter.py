import subprocess
from io import BytesIO
from os.path import join
from uuid import uuid4

import imageio
import rawpy
from exifread import process_file

from photo_db.config import Config, default_config
from photo_db.photo.photo import LocalPhoto


def convert_raw(path: str, config: Config = default_config) -> LocalPhoto:
    local_path = join(config.temp_folder(), f"{uuid4()}.jpeg")
    with open(path, "rb") as image_file:
        buf = BytesIO(image_file.read())
        buf.seek(0)
        tags = process_file(buf)
    for k, v in tags.items():
        print(f"{k}: {v}")
    buf.seek(0)
    with rawpy.imread(buf) as raw:
        rgb = raw.postprocess()
    imageio.imsave(local_path, rgb)

    subprocess.Popen(["exiftool", "-TagsFromFile", path, local_path]).wait()

    ph = LocalPhoto.from_file(local_path, config=config)
    return ph
