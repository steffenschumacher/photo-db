from datetime import UTC, datetime
from io import BytesIO
from os.path import join
from uuid import uuid4

import numpy as np
from exifread import process_file
from imagehash import ImageHash
from PIL import UnidentifiedImageError
from pydantic import BaseModel, PrivateAttr

from photo_db.config import Config, default_config

from .parsers import (
    image_hash_from,
    parse_camera,
    parse_date,
    parse_ext_hash_dimensions,
    parse_gps,
)


class Photo(BaseModel):
    uuid: str | None = None
    camera: str
    date: datetime
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    width: int
    height: int
    hash: str
    extension: str
    scanned: datetime
    #: Additional clockwise rotation (degrees: 0/90/180/270) applied on top
    #: of EXIF auto-orientation, for cases where the camera didn't record
    #: orientation correctly - set via the desktop UI's preview popup and
    #: persisted back to whichever store (local or remote) is configured.
    rotation: int = 0
    #
    _img_hash: ImageHash = PrivateAttr()
    _path: str = PrivateAttr()
    _config: Config = PrivateAttr()
    #: {clockwise_degrees: hash_string} for this photo's hash computed at
    #: each 90-degree rotation of the raw pixel grid - only populated for
    #: freshly-scanned candidates (see ``from_file``), used to detect
    #: duplicates that are the same photo physically rotated by some other
    #: tool. Never persisted (transient, upload-time-only concern).
    _rotation_hash_variants: dict[int, str] = PrivateAttr(default_factory=dict)

    def __str__(self):
        return f"Photo({self.db_path()}, {self.width}x{self.height}, {self.date}, {self.camera})"

    def __init__(self, **data):
        data.setdefault("uuid", str(uuid4()))
        data.setdefault("scanned", datetime.now())
        path = data.pop("path", None)
        config = data.pop("config", None) or default_config
        rotation_hash_variants = data.pop("rotation_hash_variants", None)
        for k in ["date", "scanned"]:
            if dt_val := data.pop(k, None):
                if isinstance(dt_val, float):
                    dt_val = datetime.fromtimestamp(dt_val, tz=UTC)
                data[k] = dt_val
        super().__init__(**data)
        if not self.date.tzinfo:
            self.date = self.date.replace(tzinfo=UTC)
        self._config = config
        # We generate the value for our private attribute
        if len(self.hash.split("-")) < 4:
            self._img_hash = image_hash_from(self.hash, config)
        self._path = path
        self._rotation_hash_variants = rotation_hash_variants or {}

    def similar_to(self, other: "Photo") -> bool:
        if not isinstance(other, self.__class__):
            raise ValueError(f"Invalid other: {other} - type: {type(other)}")
        return self.similar_to_hash(other._img_hash.hash)

    def similar_to_hash(self, hash: str | np.ndarray) -> bool:
        if isinstance(hash, str):
            nd_hash = image_hash_from(hash, self._config).hash
        elif isinstance(hash, np.ndarray):
            nd_hash = hash
        else:
            raise ValueError(f"Invalid hash: {hash} - type: {type(hash)}")
        return np.count_nonzero(self._img_hash.hash != nd_hash) <= self._config.diff_limit()

    def preferable_to(self, other: "Photo") -> bool:
        """
        Check if other photo is either older or identical date and better resolution
        :param other:
        :return:
        """
        if self.date < other.date:
            return True
        if self.date != other.date:
            return False
        # identical dates..
        if self.pixels > other.pixels:
            return True
        return False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.hash == other.hash
        return super().__eq__(other)

    @classmethod
    def from_file(cls, img_file: BytesIO | str, path: str = None, config: Config = default_config):
        try:
            if isinstance(img_file, BytesIO):
                if not path:
                    raise ValueError("Missing path arg with BytesIO")
                tags = process_file(img_file)
            elif isinstance(img_file, str):
                path = img_file
                with open(img_file, "rb") as f:
                    tags = process_file(f)
            else:
                raise ValueError(f"{img_file} is not a valid type: {type(img_file)}")
            la, lo, al = parse_gps(tags, path)
            ext, hash_variants, x, y = parse_ext_hash_dimensions(img_file, config)
            args = {
                "camera": parse_camera(tags, path),
                "date": parse_date(tags, path),
                "latitude": la,
                "longitude": lo,
                "altitude": al,
                "hash": hash_variants[0],
                "rotation_hash_variants": hash_variants,
                "width": x,
                "height": y,
                "path": path,
                "extension": ext,
                "config": config,
            }
            return Photo(**args)
        except UnidentifiedImageError as uie:
            raise ValueError(f"Not a valid photo: {uie}") from uie

    @property
    def path(self) -> str:
        return self._path

    def hash_variants(self) -> dict[int, str]:
        """Mapping of ``{clockwise_degrees: hash_string}`` for this photo's
        hash computed at each 90-degree rotation of the raw pixel grid -
        used to detect duplicates that are the same photo physically
        rotated/re-saved by some other tool (see ``LocalStore.check_hash``).
        Only populated for freshly-scanned candidates (``from_file()``);
        photos loaded from the store fall back to just their canonical
        ``{0: self.hash}`` since the source image bytes aren't at hand to
        compute the other rotations."""
        return self._rotation_hash_variants or {0: self.hash}

    @property
    def gps(self) -> str:
        if not self.latitude:
            return "N/A"
        return f"{self.latitude:.2f},{self.longitude:.2f}"

    @property
    def pixels(self) -> int:
        return self.width * self.height

    def db_path(self) -> str:
        return join(
            f"{self.date.year:04d}",
            f"{self.date.month:02d}",
            self.filename(),
        )

    def lean_dict(self) -> dict:
        """Cheap metadata only (no image bytes) - used for incremental
        sync to thick clients so they can determine locally whether a
        candidate photo already exists in the library, and browse/preview
        via a separate thumbnail fetch."""
        return {
            "uuid": self.uuid,
            "hash": self.hash,
            "date": self.date.timestamp(),
            "width": self.width,
            "height": self.height,
            "camera": self.camera,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "extension": self.extension,
            "scanned": self.scanned.timestamp(),
            "rotation": self.rotation,
        }

    def filename(self) -> str:
        d = self.date
        # Fixed-width numeric prefix (no separators) so that filenames sort
        # chronologically within a month while remaining unique: day-of-month
        # (2 digits) + hour (2) + minute (2) + second (2) + millisecond (3).
        prefix = f"{d.day:02d}{d.hour:02d}{d.minute:02d}{d.second:02d}{d.microsecond // 1000:03d}"
        return f"{prefix}_{self.uuid[-4:]}.{self.extension}".lower()


class LocalPhoto(Photo):
    local_path: str | None = None
    reject_reason: str | None = None
    duplicate_uuid: str | None = None
    duplicate_src: str | None = None
    status: str = "detected"

    def __init__(self, **data):
        super().__init__(**data)
        self.local_path = self.path

    @classmethod
    def from_file(
        cls, img_file: BytesIO | str, path: str = None, config: Config = default_config
    ) -> "LocalPhoto":
        ph = super().from_file(img_file, path, config)
        return LocalPhoto(
            **ph.model_dump(),
            path=ph.path,
            config=config,
            rotation_hash_variants=ph.hash_variants(),
        )

    def __str__(self):
        return (
            f"LocPhoto({self.local_path}, {self.width}x{self.height}, "
            f"{self.date.date()}, {self.camera}, {self.status}, {self.reject_reason})"
        )
