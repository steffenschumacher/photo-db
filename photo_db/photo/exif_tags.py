from datetime import datetime

from exif import Image
from geopy.units import arcminutes, arcseconds


def dd_to_dms_notation(deg: float) -> tuple[float, float, float]:
    """Convert signed decimal degrees to unsigned (degrees, minutes, seconds).

    EXIF GPS DMS component values are always non-negative magnitudes - the
    sign/hemisphere is conveyed separately via the corresponding *Ref tag
    (e.g. `gps_latitude_ref` "N"/"S"), so we take the absolute value here.
    """
    deg = abs(deg)
    d = float(int(deg))
    m = arcminutes(degrees=deg - d)
    s = arcseconds(arcminutes=m - int(m))
    return d, float(int(m)), s


def gps_ref(value: float, positive: str, negative: str) -> str:
    """Pick the EXIF hemisphere reference letter for a signed lat/lon value."""
    return positive if value >= 0 else negative


def update_exif(file, date: datetime = None, camera=None, gps=None):
    if not date and not camera and not gps:
        return

    with open(file, "rb") as img_f:
        img = Image(img_f.read())

    if date:
        img.set("datetime_original", date.strftime("%Y:%m:%d %H:%M:%S"))
    if camera:
        img.set("model", camera)
    if gps:
        lat, lon, alt = gps
        img.set("gps_latitude", dd_to_dms_notation(lat))
        img.set("gps_latitude_ref", gps_ref(lat, "N", "S"))
        img.set("gps_longitude", dd_to_dms_notation(lon))
        img.set("gps_longitude_ref", gps_ref(lon, "E", "W"))
        img.set("gps_altitude_ref", 0.0)
        img.set("gps_altitude", alt)
    with open(file, "wb") as new_image_file:
        new_image_file.write(img.get_file())
