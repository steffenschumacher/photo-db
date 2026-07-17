import shutil
import tempfile
from os import makedirs
from os.path import join
from pathlib import Path
from unittest import mock

from flask import Flask
from pytest import fixture

from photo_db.api.web_store import add_routes
from photo_db.client import LocalPDBClient, WebPDBClient
from photo_db.config import Config
from photo_db.db.store import StoreDB

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
def test_config() -> Config:
    """A Config instance isolated to a fresh temp directory for the test session."""
    temp_dir = tempfile.mkdtemp()
    lean_cache_dir = tempfile.mkdtemp()
    return Config(store_url=temp_dir, lean_cache_path=join(lean_cache_dir, "lean_cache.db"))


@fixture(scope="session")
def app(test_config):
    flask_app = Flask(__name__)
    add_routes(flask_app, test_config)
    flask_app.config.update(
        {
            "TESTING": True,
        }
    )
    yield flask_app


@fixture(scope="session")
def web_client(app):
    tgt = "photo_db.client.web_client.WebPDBClient.client"

    with mock.patch(tgt, RequestsClient(app.test_client())):
        yield WebPDBClient("http://127.0.0.1:5000")


@fixture(scope="session")
def local_store_client(test_config):
    yield LocalPDBClient(test_config)


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
def clean_store(test_config):
    shutil.rmtree(test_config.STORE_URL)
    makedirs(test_config.STORE_URL)
    StoreDB(test_config)


def nearly_equals(a: float, b: float, tolerance: float = 0.001) -> bool:
    return abs(a - b) < tolerance
