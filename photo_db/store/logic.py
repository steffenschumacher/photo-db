from io import BytesIO
from os import chown, makedirs
from os.path import exists, join, sep

from ..api import DuplicateException, SimilarException
from ..config import Config
from ..db import store as db
from ..photo import Photo

if not exists(Config.STORE_URL):
    makedirs(Config.STORE_URL)
db.init_store_db()


class LocalStore:
    @classmethod
    def check_hash(cls, ph: Photo) -> bool:
        tpl = "Uploaded photo is {} existing photo"
        if uuid := db.lookup_hash(ph.hash):
            raise DuplicateException(uuid, tpl.format("duplicate of"))

        for ext_hash, uuid in db.get_hashes().items():
            if ph.similar_to_hash(ext_hash):
                existing = db.get_photo(uuid)
                if existing.preferable_to(ph):
                    raise SimilarException(uuid, tpl.format("too similar to preferable"))
        db.insert_photo(ph)

    @classmethod
    def upload(cls, photo: bytes) -> str:
        try:
            ph = Photo.from_file(BytesIO(photo), "uploaded.jpg")
            cls.check_hash(ph)
            photo_path = cls.abs_folder(ph.db_path())
        except SimilarException as sim:
            raise sim
        except DuplicateException as dup:
            # if photo exists in db, but not in fs, we also store it.
            # Cases: deleted locally or pre_check
            ph.uuid = dup.uuid
            photo_path = cls.abs_folder(ph.db_path())
            if exists(photo_path):
                raise dup
        try:
            with open(photo_path, "wb") as new_pic:
                new_pic.write(photo)
            if Config.FILE_GID or Config.FILE_UID:
                # -1 means dont change
                uid = Config.FILE_UID or -1
                gid = Config.FILE_GID or -1
                chown(photo_path, uid, gid)
            return ph.uuid
        except Exception as e:
            print(e)

    @classmethod
    def get_photo(cls, uuid: str) -> Photo:
        if ph := db.get_photo(uuid):
            return ph

    @classmethod
    def read_photo(cls, ph: Photo) -> bytes:
        with open(cls.abs_folder(ph.db_path()), "rb") as pic:
            return pic.read()

    @classmethod
    def get_hashes(cls) -> dict[str, str]:
        return db.get_hashes()

    @classmethod
    def abs_folder(cls, db_path: str) -> str:
        db_path_parts = db_path.split(sep)
        filename = db_path_parts.pop()
        db_dir = join(Config.STORE_URL, *db_path_parts)
        if not exists(db_dir):
            makedirs(db_dir)
        return join(db_dir, filename)
