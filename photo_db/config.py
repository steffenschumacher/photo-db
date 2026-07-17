from dotenv import load_dotenv
from environs import Env
from os.path import join
import tempfile

env = Env()
load_dotenv()


class Config:
    STORE_URL = env.str("PH_STORE_URL", "/photodb").rstrip("/")
    SSL_VERIFY = env.bool("PH_SSL_VERIFY", False)
    STORE_USER = env.str("PH_STORE_USER", "peterpan")
    STORE_PASS = env.str("PH_STORE_PASS", "jegergod!QAZ2wsx")
    # https://medium.com/@somilshah112/how-to-find-duplicate-or-similar-images-quickly-with-python-2d636af9452f
    HASH_SIZE = env.int("PH_HASH_SIZE", 70)
    SIMILARITY = env.int("PH_SIMILARITY", 97)
    FILE_UID = env.int("PH_UID", None)
    FILE_GID = env.int("PH_GID", None)
    _TEMP_FOLDER = None

    @classmethod
    def diff_limit(cls):
        hs = cls.HASH_SIZE
        if 1 <= cls.SIMILARITY <= 99:
            return int((1 - cls.SIMILARITY / 100) * (hs**2))
        raise ValueError(f"Invalid similarity: {cls.SIMILARITY}")

    @classmethod
    def temp_folder(cls) -> str:
        if cls._TEMP_FOLDER is None:
            cls._TEMP_FOLDER = tempfile.mkdtemp(prefix="photodb_import")
        return cls._TEMP_FOLDER

    @classmethod
    def info(cls) -> str:
        kvs = {
            "url": cls.STORE_URL,
            "user": cls.STORE_USER,
            "pw": cls.STORE_PASS,
            "hash": cls.HASH_SIZE,
            "similarity": cls.SIMILARITY,
        }
        strings = [f"{k}: {v}" for k, v in kvs.items()]

        msg = f"Config({', '.join(strings)})"
        return msg


__all__ = ["Config"]
