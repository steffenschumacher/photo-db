from datetime import UTC, datetime
from io import BytesIO
from os.path import join
from uuid import uuid4

import numpy as np
from exifread import process_file
from imagehash import ImageHash
from PIL import UnidentifiedImageError
from pydantic import BaseModel, PrivateAttr

from photo_db.config import Config

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
    #
    _img_hash: ImageHash = PrivateAttr()
    _path: str = PrivateAttr()

    def __str__(self):
        return f"Photo({self.db_path()}, {self.width}x{self.height}, {self.date}, {self.camera})"

    def __init__(self, **data):
        data.setdefault("uuid", str(uuid4()))
        data.setdefault("scanned", datetime.now())
        path = data.pop("path", None)
        for k in ["date", "scanned"]:
            if dt_val := data.pop(k, None):
                if isinstance(dt_val, float):
                    dt_val = datetime.fromtimestamp(dt_val, tz=UTC)
                data[k] = dt_val
        super().__init__(**data)
        if not self.date.tzinfo:
            self.date = self.date.replace(tzinfo=UTC)
        # We generate the value for our private attribute
        if len(self.hash.split("-")) < 4:
            self._img_hash = image_hash_from(self.hash)
        self._path = path

    def similar_to(self, other: "Photo") -> bool:
        if not isinstance(other, self.__class__):
            raise ValueError(f"Invalid other: {other} - type: {type(other)}")
        return self.similar_to_hash(other._img_hash.hash)

    def similar_to_hash(self, hash: str | np.ndarray) -> bool:
        if isinstance(hash, str):
            nd_hash = image_hash_from(hash).hash
        elif isinstance(hash, np.ndarray):
            nd_hash = hash
        else:
            raise ValueError(f"Invalid hash: {hash} - type: {type(hash)}")
        return np.count_nonzero(self._img_hash.hash != nd_hash) <= Config.diff_limit()

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
    def from_file(cls, img_file: BytesIO | str, path: str = None):
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
            ext, str_hash, x, y = parse_ext_hash_dimensions(img_file)
            args = {
                "camera": parse_camera(tags, path),
                "date": parse_date(tags, path),
                "latitude": la,
                "longitude": lo,
                "altitude": al,
                "hash": str_hash,
                "width": x,
                "height": y,
                "path": path,
                "extension": ext,
            }
            return Photo(**args)
        except UnidentifiedImageError as uie:
            raise ValueError(f"Not a valid photo: {uie}") from uie

    @property
    def path(self) -> str:
        return self._path

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
            f"{self.date.year}",
            f"{self.date.month}",
            self.filename(),
        )

    def filename(self) -> str:
        return f"{self.date.strftime('%d-%H%M%S')}-{self.uuid[-4:]}.{self.extension}".lower()


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
    def from_file(cls, img_file: BytesIO | str, path: str = None) -> "LocalPhoto":
        ph = super().from_file(img_file, path)
        return LocalPhoto(**ph.model_dump(), path=ph.path)

    def __str__(self):
        return (
            f"LocPhoto({self.local_path}, {self.width}x{self.height}, "
            f"{self.date.date()}, {self.camera}, {self.status}, {self.reject_reason})"
        )
