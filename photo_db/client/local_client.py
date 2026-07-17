from io import BytesIO
from ..config import Config
from .abstract_client import AbstractPDBClient
from ..photo import Photo
from photo_db.store.logic import LocalStore


class LocalPDBClient(AbstractPDBClient):
    def check_hash(self, ph: Photo) -> bool:
        return LocalStore.check_hash(hash)

    def upload(self, image: bytes):
        return LocalStore.upload(image)

    def get(self, uuid: str) -> bytes:
        return LocalStore.read_photo(self.get_meta(uuid))

    def get_meta(self, uuid: str) -> Photo:
        return LocalStore.get_photo(uuid)

    def hashes(self) -> dict[str, str]:
        return LocalStore.get_hashes()
