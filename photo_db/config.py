import tempfile
from os.path import exists, expanduser, join

from dotenv import load_dotenv
from environs import Env

env = Env()
load_dotenv()


class Config:
    """Application configuration.

    Instantiate explicitly (``Config()``) to read fresh values from the
    environment, or pass explicit keyword arguments to override individual
    settings (handy for tests / multiple stores in the same process). Values
    are captured at construction time rather than read from mutable class
    attributes, so each ``Config`` instance is independent and safe to pass
    around via dependency injection instead of relying on a shared global.
    """

    def __init__(
        self,
        store_url: str | None = None,
        ssl_verify: bool | None = None,
        store_user: str | None = None,
        store_pass: str | None = None,
        hash_size: int | None = None,
        similarity: int | None = None,
        file_uid: int | None = None,
        file_gid: int | None = None,
        lean_cache_path: str | None = None,
    ):
        self.STORE_URL = (
            store_url if store_url is not None else env.str("PH_STORE_URL", "/photodb")
        ).rstrip("/")
        self.SSL_VERIFY = ssl_verify if ssl_verify is not None else env.bool("PH_SSL_VERIFY", False)
        self.STORE_USER = store_user if store_user is not None else env.str("PH_STORE_USER", None)
        self.STORE_PASS = store_pass if store_pass is not None else env.str("PH_STORE_PASS", None)
        # https://medium.com/@somilshah112/how-to-find-duplicate-or-similar-images-quickly-with-python-2d636af9452f
        self.HASH_SIZE = hash_size if hash_size is not None else env.int("PH_HASH_SIZE", 70)
        self.SIMILARITY = similarity if similarity is not None else env.int("PH_SIMILARITY", 97)
        self.FILE_UID = file_uid if file_uid is not None else env.int("PH_UID", None)
        self.FILE_GID = file_gid if file_gid is not None else env.int("PH_GID", None)
        # Local sqlite cache of lean (metadata-only) sync data from the
        # central store, used by the thick client to browse/dedup-check
        # without a network round trip per photo. Defaults to a per-user
        # location outside the (possibly remote-mirrored) STORE_URL.
        self.LEAN_CACHE_PATH = lean_cache_path or env.str(
            "PH_LEAN_CACHE_PATH", join(expanduser("~"), ".photodb", "lean_cache.db")
        )
        self._temp_folder: str | None = None

    def diff_limit(self) -> int:
        hs = self.HASH_SIZE
        if 1 <= self.SIMILARITY <= 99:
            return int((1 - self.SIMILARITY / 100) * (hs**2))
        raise ValueError(f"Invalid similarity: {self.SIMILARITY}")

    def temp_folder(self) -> str:
        if self._temp_folder is None:
            self._temp_folder = tempfile.mkdtemp(prefix="photodb_import")
        return self._temp_folder

    def info(self) -> str:
        kvs = {
            "url": self.STORE_URL,
            "user": self.STORE_USER,
            "pw": "***" if self.STORE_PASS else None,
            "hash": self.HASH_SIZE,
            "similarity": self.SIMILARITY,
        }
        strings = [f"{k}: {v}" for k, v in kvs.items()]

        msg = f"Config({', '.join(strings)})"
        return msg

    def save_env_file(self, path: str = ".env") -> None:
        """Persist the current settings as ``PH_*`` variables in a
        dotenv file, creating it if necessary. Used by the desktop UI's
        Settings dialog so changes survive across app restarts."""
        from dotenv import set_key

        if not exists(path):
            open(path, "a").close()
        pairs = {
            "PH_STORE_URL": self.STORE_URL,
            "PH_SSL_VERIFY": str(self.SSL_VERIFY),
            "PH_STORE_USER": self.STORE_USER,
            "PH_STORE_PASS": self.STORE_PASS,
            "PH_HASH_SIZE": str(self.HASH_SIZE),
            "PH_SIMILARITY": str(self.SIMILARITY),
            "PH_LEAN_CACHE_PATH": self.LEAN_CACHE_PATH,
        }
        for key, value in pairs.items():
            if value is not None:
                set_key(path, key, str(value))


# Default, process-wide instance built from environment variables at import
# time. Entry points (manage.py, pdbscanner.py, app.py) use this by default;
# pass an explicit Config instance anywhere dependency injection is wanted
# (e.g. tests constructing their own Config with overrides).
default_config = Config()

__all__ = ["Config", "default_config"]
