from datetime import datetime
from fractions import Fraction

import piexif
import pillow_heif

from .exif_tags import dd_to_dms_notation, gps_ref

pillow_heif.register_heif_opener()

_EMPTY_EXIF: dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}


def _rational(value: float, denominator: int = 10_000) -> tuple[int, int]:
    frac = Fraction(value).limit_denominator(denominator)
    return frac.numerator, frac.denominator


def _gps_ifd(lat: float, lon: float, alt: float) -> dict:
    lat_d, lat_m, lat_s = dd_to_dms_notation(lat)
    lon_d, lon_m, lon_s = dd_to_dms_notation(lon)
    return {
        piexif.GPSIFD.GPSLatitudeRef: gps_ref(lat, "N", "S"),
        piexif.GPSIFD.GPSLatitude: (
            _rational(lat_d, 1),
            _rational(lat_m, 1),
            _rational(lat_s),
        ),
        piexif.GPSIFD.GPSLongitudeRef: gps_ref(lon, "E", "W"),
        piexif.GPSIFD.GPSLongitude: (
            _rational(lon_d, 1),
            _rational(lon_m, 1),
            _rational(lon_s),
        ),
        piexif.GPSIFD.GPSAltitudeRef: 0 if alt >= 0 else 1,
        piexif.GPSIFD.GPSAltitude: _rational(abs(alt)),
    }


def update_heic(file, date: datetime = None, camera=None, gps=None):
    """Update EXIF date/camera/GPS metadata on a HEIC/HEIF file in place.

    HEIF containers embed the same "Exif\\x00\\x00" + TIFF byte structure
    used in a JPEG APP1 segment (`pillow_heif` exposes it verbatim via
    `HeifFile.info["exif"]`), so we can decode/patch/re-encode it with
    `piexif` and write it straight back into the container.

    Caveat (verified during implementation): `exifread` - which
    `Photo.from_file` uses to *read* EXIF - fails to parse the HEIC "Exif"
    box layout written by `pillow_heif`'s own HEIF encoder (this reproduces
    even for an untouched, freshly-encoded file, i.e. it's not something
    introduced here). Camera-native HEIC files (e.g. real iPhone photos) may
    use a different, exifread-compatible box layout - this has not been
    verified against real camera samples. Round-tripping writes made by this
    function have been verified via `pillow_heif`/`piexif` directly; treat
    `Photo.from_file()` on a HEIC written by this function as unverified
    until tested against real-world samples.
    """
    if not date and not camera and not gps:
        return

    heif_file = pillow_heif.open_heif(file)
    raw_exif = heif_file.info.get("exif")
    exif_dict = piexif.load(raw_exif) if raw_exif else dict(_EMPTY_EXIF)

    if date:
        stamp = date.strftime("%Y:%m:%d %H:%M:%S").encode()
        exif_dict["0th"][piexif.ImageIFD.DateTime] = stamp
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = stamp
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = stamp
    if camera:
        exif_dict["0th"][piexif.ImageIFD.Model] = camera.encode()
    if gps:
        lat, lon, alt = gps
        exif_dict["GPS"] = _gps_ifd(lat, lon, alt)

    heif_file.info["exif"] = piexif.dump(exif_dict)
    heif_file.save(file, quality=-1)
