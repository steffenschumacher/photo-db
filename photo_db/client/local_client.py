from datetime import UTC, datetime

from ..config import Config, default_config
from ..photo import Photo
from ..store.logic import LocalStore
from .abstract_client import AbstractPDBClient


class LocalPDBClient(AbstractPDBClient):
    def __init__(self, config: Config = default_config):
        self.config = config
        self.store = LocalStore(config)

    def check_hash(self, ph: Photo) -> bool:
        return self.store.check_hash(ph)

    def upload(self, image: bytes):
        return self.store.upload(image)

    def get(self, uuid: str) -> bytes:
        return self.store.read_photo(self.get_meta(uuid))

    def get_thumbnail(self, uuid: str) -> bytes:
        return self.store.get_thumbnail(self.get_meta(uuid))

    def get_meta(self, uuid: str) -> Photo:
        return self.store.get_photo(uuid)

    def hashes(self) -> dict[str, str]:
        return self.store.get_hashes()

    def sync_since(self, since: float | None = None, limit: int = 5000) -> dict:
        since_dt = datetime.fromtimestamp(since, tz=UTC) if since is not None else None
        photos = self.store.since(since_dt, limit)
        return {
            "photos": [ph.lean_dict() for ph in photos],
            "next_since": photos[-1].scanned.timestamp() if photos else since,
        }
