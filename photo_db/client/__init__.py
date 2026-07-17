from .abstract_client import AbstractPDBClient
from .local_client import LocalPDBClient
from .web_client import WebPDBClient

__all__ = ["AbstractPDBClient", "LocalPDBClient", "WebPDBClient", "init_client"]


def init_client(url: str = None) -> AbstractPDBClient:
    from os.path import exists

    from ..config import Config

    url = url or Config.STORE_URL

    if url.lower().startswith("http"):
        return WebPDBClient(url.lower())
    elif exists(url):
        Config.STORE_URL = url
        return LocalPDBClient()
    else:
        raise ValueError(f"Invalid store uri: {url}")
