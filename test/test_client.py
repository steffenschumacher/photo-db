import tempfile
from os.path import join

from photo_db.client import LocalPDBClient, WebPDBClient, init_client
from photo_db.config import Config


def test_init_client():
    Config.STORE_URL = "http://localhost:5000"
    client = init_client()
    assert isinstance(client, WebPDBClient)
    temp_dir = tempfile.mkdtemp()
    Config.STORE_URL = temp_dir
    Config.STORE_DB_URL = join(temp_dir, ".photo.db")
    client = init_client()
    assert isinstance(client, LocalPDBClient)
