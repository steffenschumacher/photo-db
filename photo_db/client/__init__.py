from .abstract_client import AbstractPDBClient
from .local_client import LocalPDBClient
from .web_client import WebPDBClient


def init_client(url: str = None) -> AbstractPDBClient:
    from ..config import Config
    from os.path import exists

    url = url or Config.STORE_URL

    if url.lower().startswith("http"):
        return WebPDBClient(url.lower())
    elif exists(url):
        Config.STORE_URL = url
        return LocalPDBClient()
    else:
        raise ValueError(f"Invalid store uri: {url}")
