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


def test_init_client_creates_not_yet_existing_local_path():
    """A brand new local store path (first run, nothing scanned yet) is a
    valid choice, not an error - LocalStore creates the folder itself."""
    temp_dir = tempfile.mkdtemp()
    new_store_path = f"{temp_dir}/not-created-yet"
    config = Config(store_url=new_store_path)

    client = init_client(config=config)

    assert isinstance(client, LocalPDBClient)
    from os.path import exists

    assert exists(new_store_path)


def test_init_client_rejects_empty_store_url():
    import pytest

    config = Config(store_url="")
    with pytest.raises(ValueError):
        init_client(config=config)


def test_local_client_rotate_persists_and_wraps(local_store_client, clean_store):
    from .conftest import STATIC_DIR

    uuid = local_store_client.upload((STATIC_DIR / "08-190641-4631.jpeg").read_bytes())
    assert local_store_client.rotate(uuid, 90) == 90
    assert local_store_client.rotate(uuid, 90) == 180
    assert local_store_client.rotate(uuid, 270) == 90
    assert local_store_client.get_meta(uuid).rotation == 90


def test_local_client_rotate_unknown_uuid_raises(local_store_client, clean_store):
    import pytest

    with pytest.raises(ValueError):
        local_store_client.rotate("does-not-exist", 90)
