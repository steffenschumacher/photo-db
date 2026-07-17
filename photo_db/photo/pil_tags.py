from datetime import datetime
from PIL import Image
from pillow_heif import register_heif_opener
from .exif_tags import dd_to_dms_notation

register_heif_opener()


def update_heic(file, date: datetime = None, camera=None, gps=None):
    img = Image.open(file)
    """
    https://stackoverflow.com/questions/72522522/how-to-extract-gps-location-from-heic-files
    """
    raise NotImplementedError("Implement when need occurs")
