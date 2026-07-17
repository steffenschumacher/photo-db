from datetime import datetime
from exif import Image
from geopy.units import arcminutes, arcseconds


def dd_to_dms_notation(deg: float) -> tuple[float, float, float]:
    d = float(int(deg))
    m = arcminutes(degrees=deg - d)
    s = arcseconds(arcminutes=m - int(m))
    return d, float(int(m)), s


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
        img.set("gps_latitude_ref", "N" if lat >= 0 else "S")
        img.set("gps_longitude", dd_to_dms_notation(lon))
        img.set("gps_longitude_ref", "E" if lon >= 0 else "W")
        img.set("gps_altitude_ref", 0.0)
        img.set("gps_altitude", alt)
    with open(file, "wb") as new_image_file:
        new_image_file.write(img.get_file())
