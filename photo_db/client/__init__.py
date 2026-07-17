from ..config import Config, default_config
from .abstract_client import AbstractPDBClient
from .local_client import LocalPDBClient
from .web_client import WebPDBClient

__all__ = ["AbstractPDBClient", "LocalPDBClient", "WebPDBClient", "init_client"]


def init_client(url: str = None, config: Config = default_config) -> AbstractPDBClient:
    url = url or config.STORE_URL
    if not url:
        raise ValueError("No store configured - set a local folder path or http(s):// URL")

    if url.lower().startswith("http"):
        return WebPDBClient(url, config=config)
    # Any non-http(s) value is treated as a local folder path. LocalStore
    # creates the folder itself if it doesn't exist yet, so a brand new,
    # not-yet-existing path is a valid (first-run) choice, not an error.
    config.STORE_URL = url
    return LocalPDBClient(config)
