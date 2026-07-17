from ..config import Config, default_config
from .abstract_client import AbstractPDBClient
from .local_client import LocalPDBClient
from .web_client import WebPDBClient

__all__ = ["AbstractPDBClient", "LocalPDBClient", "WebPDBClient", "init_client"]


def init_client(url: str = None, config: Config = default_config) -> AbstractPDBClient:
    from os.path import exists

    url = url or config.STORE_URL

    if url.lower().startswith("http"):
        return WebPDBClient(url.lower(), config=config)
    elif exists(url):
        config.STORE_URL = url
        return LocalPDBClient(config)
    else:
        raise ValueError(f"Invalid store uri: {url}")
