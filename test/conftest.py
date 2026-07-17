import shutil
import tempfile
from os import makedirs
from os.path import join
from pathlib import Path
from unittest import mock

from pytest import fixture

from photo_db.app import create_app
from photo_db.client import LocalPDBClient, WebPDBClient
from photo_db.config import Config
from photo_db.db import store as store_db

# Fixture images live alongside this file, not relative to the process's
# current working directory - resolve absolutely so tests pass regardless of
# where `pytest` is invoked from (see docs/PROJECT_STATUS_AND_PLAN.md, "Test
# suite: current real state").
STATIC_DIR = Path(__file__).parent / "static"


class RequestsClient:
    def __init__(self, client):
        self.client = client

    def post(self, *args, **kwargs):
        kwargs.pop("verify", None)
        return self.client.post(*args, **kwargs)

    def get(self, *args, **kwargs):
        kwargs.pop("verify", None)
        return self.client.get(*args, **kwargs)


@fixture(scope="session")
def app():
    temp_dir = tempfile.mkdtemp()
    Config.STORE_URL = temp_dir
    Config.STORE_DB_URL = join(temp_dir, ".photo.db")

    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    yield app


@fixture(scope="session")
def web_client(app):
    tgt = "photo_db.client.web_client.WebPDBClient.client"

    with mock.patch(tgt, RequestsClient(app.test_client())):
        yield WebPDBClient("http://127.0.0.1:5000")


@fixture(scope="session")
def local_store_client():
    temp_dir = tempfile.mkdtemp()
    Config.STORE_URL = temp_dir
    Config.STORE_DB_URL = join(temp_dir, ".photo.db")
    store_db.init_store_db()
    yield LocalPDBClient()


@fixture()
def exif_incomplete_photo() -> str:
    filename = "25-121007-33d0.jpeg"
    temp_dir = tempfile.mkdtemp()
    x = shutil.copyfile(STATIC_DIR / filename, join(temp_dir, filename))
    yield x


@fixture()
def raw_photo() -> str:
    filename = "15175111__DSC04832.ARW"
    temp_dir = tempfile.mkdtemp()
    x = shutil.copyfile(STATIC_DIR / filename, join(temp_dir, filename))
    yield x


@fixture()
def clean_store():
    shutil.rmtree(Config.STORE_URL)
    makedirs(Config.STORE_URL)
    store_db.init_store_db()


def nearly_equals(a: float, b: float, tolerance: float = 0.001) -> bool:
    return abs(a - b) < tolerance
