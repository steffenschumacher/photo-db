from ..photo import Photo


class AbstractPDBClient:
    def check_hash(self, ph: Photo) -> bool:
        raise NotImplementedError("")

    def upload(self, image: bytes) -> str:
        raise NotImplementedError("")

    def get(self, uuid: str) -> bytes:
        raise NotImplementedError("")

    def get_thumbnail(self, uuid: str) -> bytes:
        raise NotImplementedError("")

    def get_meta(self, uuid: str) -> Photo:
        raise NotImplementedError("")

    def hashes(self) -> dict[str, str]:
        raise NotImplementedError("")

    def sync_since(self, since: float | None = None, limit: int = 5000) -> dict:
        raise NotImplementedError("")
