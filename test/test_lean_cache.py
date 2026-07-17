"""Tests for LeanCache and the /sync lean incremental-sync endpoint."""

import tempfile
from datetime import UTC, datetime

from photo_db.config import Config
from photo_db.db.lean_cache import LeanCache

from .conftest import STATIC_DIR


def _sample_bytes(filename: str = "08-190641-4631.jpeg") -> bytes:
    with open(STATIC_DIR / filename, "rb") as f:
        return f.read()


def _lean_config() -> Config:
    return Config(lean_cache_path=tempfile.mktemp(suffix=".db"))


def test_lean_cache_upsert_and_query_by_month():
    cache = LeanCache(_lean_config())
    row = {
        "uuid": "abc-123",
        "hash": "somehash",
        "date": 1_700_000_000,
        "width": 100,
        "height": 100,
        "camera": "TestCam",
        "latitude": None,
        "longitude": None,
        "extension": "jpeg",
        "scanned": 1_700_000_100,
        "rotation": 0,
    }
    cache.upsert_many([row])

    assert cache.count() == 1
    assert cache.is_known_hash("somehash") == "abc-123"
    assert cache.is_known_hash("missing") is None

    d = datetime.fromtimestamp(1_700_000_000, tz=UTC)
    results = cache.query_by_month(d.year, d.month)
    assert len(results) == 1
    assert results[0]["uuid"] == "abc-123"

    assert (d.year, d.month) in cache.available_months()


def test_lean_cache_last_synced_roundtrip():
    cache = LeanCache(_lean_config())
    assert cache.last_synced() is None
    cache.set_last_synced(12345.0)
    assert cache.last_synced() == 12345.0
    cache.set_last_synced(67890.0)
    assert cache.last_synced() == 67890.0


def test_lean_cache_sync_from_local_client(local_store_client, clean_store):
    local_store_client.upload(_sample_bytes())
    local_store_client.upload(_sample_bytes("25-121007-33d0.jpeg"))

    cache = LeanCache(_lean_config())
    synced = cache.sync(local_store_client)
    assert synced == 2
    assert cache.count() == 2
    assert cache.last_synced() is not None

    # A second sync with nothing new should be a no-op.
    synced_again = cache.sync(local_store_client)
    assert synced_again == 0
    assert cache.count() == 2


def test_web_client_sync_since_returns_lean_rows(web_client, clean_store):
    web_client.upload(_sample_bytes())
    result = web_client.sync_since()
    assert len(result["photos"]) == 1
    photo = result["photos"][0]
    assert set(photo.keys()) == {
        "uuid",
        "hash",
        "date",
        "width",
        "height",
        "camera",
        "latitude",
        "longitude",
        "extension",
        "scanned",
        "rotation",
    }


def test_lean_cache_sync_from_web_client(web_client, clean_store):
    web_client.upload(_sample_bytes())
    cache = LeanCache(_lean_config())
    synced = cache.sync(web_client)
    assert synced == 1
    assert cache.count() == 1
