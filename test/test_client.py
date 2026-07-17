import tempfile

from photo_db.client import LocalPDBClient, WebPDBClient, init_client
from photo_db.config import Config


def test_init_client():
    client = init_client("http://localhost:5000")
    assert isinstance(client, WebPDBClient)

    temp_dir = tempfile.mkdtemp()
    config = Config(store_url=temp_dir)
    client = init_client(config=config)
    assert isinstance(client, LocalPDBClient)
