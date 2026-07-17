from io import BytesIO
from os import chown, makedirs
from os.path import exists, join, sep

from ..api import DuplicateException, SimilarException
from ..config import Config, default_config
from ..db.store import StoreDB
from ..photo import Photo


class LocalStore:
    """Filesystem + SQLite backed photo library.

    Instantiated with an explicit ``Config`` (dependency injection) so tests
    and callers can point multiple, isolated stores at different locations
    in the same process instead of relying on shared global state.
    """

    def __init__(self, config: Config = default_config):
        self.config = config
        if not exists(config.STORE_URL):
            makedirs(config.STORE_URL)
        self.db = StoreDB(config)

    def check_hash(self, ph: Photo) -> bool:
        tpl = "Uploaded photo is {} existing photo"
        if uuid := self.db.lookup_hash(ph.hash):
            raise DuplicateException(uuid, tpl.format("duplicate of"))

        for ext_hash, uuid in self.db.get_hashes().items():
            if ph.similar_to_hash(ext_hash):
                existing = self.db.get_photo(uuid)
                if existing.preferable_to(ph):
                    raise SimilarException(uuid, tpl.format("too similar to preferable"))
        self.db.insert_photo(ph)

    def upload(self, photo: bytes) -> str:
        try:
            ph = Photo.from_file(BytesIO(photo), "uploaded.jpg", config=self.config)
            self.check_hash(ph)
            photo_path = self.abs_folder(ph.db_path())
        except SimilarException as sim:
            raise sim
        except DuplicateException as dup:
            # if photo exists in db, but not in fs, we also store it.
            # Cases: deleted locally or pre_check
            ph.uuid = dup.uuid
            photo_path = self.abs_folder(ph.db_path())
            if exists(photo_path):
                raise dup
        with open(photo_path, "wb") as new_pic:
            new_pic.write(photo)
        if self.config.FILE_GID or self.config.FILE_UID:
            # -1 means dont change
            uid = self.config.FILE_UID or -1
            gid = self.config.FILE_GID or -1
            chown(photo_path, uid, gid)
        return ph.uuid

    def get_photo(self, uuid: str) -> Photo:
        if ph := self.db.get_photo(uuid):
            return ph

    def read_photo(self, ph: Photo) -> bytes:
        with open(self.abs_folder(ph.db_path()), "rb") as pic:
            return pic.read()

    def get_hashes(self) -> dict[str, str]:
        return self.db.get_hashes()

    def abs_folder(self, db_path: str) -> str:
        db_path_parts = db_path.split(sep)
        filename = db_path_parts.pop()
        db_dir = join(self.config.STORE_URL, *db_path_parts)
        if not exists(db_dir):
            makedirs(db_dir)
        return join(db_dir, filename)


__all__ = ["LocalStore"]
