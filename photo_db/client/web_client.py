from io import BytesIO

from requests import Response, get, post

from ..config import Config, default_config
from ..exceptions import DuplicateException, SimilarException
from ..photo import Photo
from .abstract_client import AbstractPDBClient


def _response_json(r: Response) -> dict:
    """Read a JSON body from either a real requests.Response (``.json()`` is
    a method) or Flask's test client response (``.json`` is a property)."""
    return r.json() if callable(r.json) else r.json


def _response_content(r: Response) -> bytes:
    """Read the raw body from either a real requests.Response (``.content``)
    or Flask's test client response (``.data``)."""
    return r.content if hasattr(r, "content") else r.data


class WebClient:
    @classmethod
    def post(cls, *args, **kwargs) -> Response:
        return post(*args, **kwargs)

    @classmethod
    def get(cls, *args, **kwargs) -> Response:
        return get(*args, **kwargs)


class WebPDBClient(AbstractPDBClient):
    def __init__(self, url=None, user=None, pwd=None, config: Config = default_config):
        self.config = config
        self.url = url or config.STORE_URL
        self.http_kwargs = {
            "auth": (user or config.STORE_USER, pwd or config.STORE_PASS),
            "verify": config.SSL_VERIFY,
        }
        if not config.SSL_VERIFY:
            import urllib3

            urllib3.disable_warnings()

    @property
    def client(self) -> WebClient:
        return WebClient

    def check_hash(self, ph: Photo) -> bool:
        url = f"{self.url}/pre_check"
        client = self.client
        r = client.post(url, json=ph.model_dump_json(), **self.http_kwargs)
        self.process_response(r)
        return True

    def upload(self, image: bytes) -> str:
        url = f"{self.url}/upload"
        r = self.client.post(url, data=BytesIO(image), **self.http_kwargs)
        self.process_response(r)
        return r.text

    def get(self, uuid: str) -> bytes:
        url = f"{self.url}/image/{uuid}"
        r = self.client.get(url, **self.http_kwargs)
        self.process_response(r)
        return _response_content(r)

    def get_thumbnail(self, uuid: str) -> bytes:
        url = f"{self.url}/thumb/{uuid}"
        r = self.client.get(url, **self.http_kwargs)
        self.process_response(r)
        return _response_content(r)

    def get_meta(self, uuid: str) -> Photo:
        url = f"{self.url}/meta/{uuid}"
        r = self.client.get(url, **self.http_kwargs)
        self.process_response(r)
        return Photo(**_response_json(r), config=self.config)

    def rotate(self, uuid: str, delta: int) -> int:
        url = f"{self.url}/rotate/{uuid}"
        r = self.client.post(url, json={"delta": delta}, **self.http_kwargs)
        self.process_response(r)
        return _response_json(r)["rotation"]

    def hashes(self) -> dict[str, str]:
        url = f"{self.url}/hashes"
        r = self.client.get(url, **self.http_kwargs)
        self.process_response(r)
        return _response_json(r)

    def sync_since(self, since: float | str | None = None, limit: int = 5000) -> dict:
        query = f"limit={limit}"
        if since is not None:
            query += f"&since={since}"
        url = f"{self.url}/sync?{query}"
        r = self.client.get(url, **self.http_kwargs)
        self.process_response(r)
        return _response_json(r)

    def process_response(self, r: Response):
        if r.status_code == 409:
            json = _response_json(r)
            if json:
                if pdb_code := json.get("pdb_code"):
                    uuid = json["uuid"]
                    msg = json["msg"]
                    if pdb_code == 1001:
                        raise DuplicateException(uuid, msg)
                    elif pdb_code == 1002:
                        raise SimilarException(uuid, msg)
                raise ValueError(f"Invalid exception json: {json}")
        elif hasattr(r, "raise_for_status"):
            r.raise_for_status()
        elif r.status_code >= 400:
            # Flask's test client (used by tests, via RequestsClient) has no
            # raise_for_status() - surface non-2xx/409 responses ourselves
            # so callers (e.g. rotate() on an unknown uuid -> 404) don't
            # silently fall through to indexing a None JSON body.
            raise ValueError(f"Request failed with status {r.status_code}: {_response_content(r)}")
