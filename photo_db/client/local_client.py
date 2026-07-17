from photo_db.store.logic import LocalStore

from ..photo import Photo
from .abstract_client import AbstractPDBClient


class LocalPDBClient(AbstractPDBClient):
    def check_hash(self, ph: Photo) -> bool:
        return LocalStore.check_hash(ph)

    def upload(self, image: bytes):
        return LocalStore.upload(image)

    def get(self, uuid: str) -> bytes:
        return LocalStore.read_photo(self.get_meta(uuid))

    def get_meta(self, uuid: str) -> Photo:
        return LocalStore.get_photo(uuid)

    def hashes(self) -> dict[str, str]:
        return LocalStore.get_hashes()
