"""Regression tests for photo_db.db.store.StoreDB.

These exercise SQL paths that were previously broken (search() had a stray
trailing paren and never returned its results; get_photo()/lookup_hash()
interpolated user-controlled values directly into SQL text instead of using
parameterized queries).
"""

import tempfile
from datetime import UTC, datetime

from photo_db.config import Config
from photo_db.db.store import StoreDB
from photo_db.photo import Photo

from .conftest import STATIC_DIR


def make_db() -> StoreDB:
    config = Config(store_url=tempfile.mkdtemp())
    return StoreDB(config)


def test_insert_and_get_photo():
    db = make_db()
    ph = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.insert_photo(ph)

    fetched = db.get_photo(ph.uuid)
    assert fetched is not None
    assert fetched.uuid == ph.uuid
    assert fetched.hash == ph.hash


def test_get_photo_not_found_returns_none():
    db = make_db()
    assert db.get_photo("does-not-exist") is None


def test_lookup_hash():
    db = make_db()
    ph = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.insert_photo(ph)

    assert db.lookup_hash(ph.hash) == ph.uuid
    assert db.lookup_hash("nonexistent-hash") is None


def test_get_hashes():
    db = make_db()
    ph1 = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    ph2 = Photo.from_file(str(STATIC_DIR / "25-121007-33d0.jpeg"))
    db.insert_photo(ph1)
    db.insert_photo(ph2)

    hashes = db.get_hashes()
    assert hashes[ph1.hash] == ph1.uuid
    assert hashes[ph2.hash] == ph2.uuid


def test_search_no_criteria_returns_all():
    db = make_db()
    ph1 = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    ph2 = Photo.from_file(str(STATIC_DIR / "25-121007-33d0.jpeg"))
    db.insert_photo(ph1)
    db.insert_photo(ph2)

    results = db.search()
    assert {r.uuid for r in results} == {ph1.uuid, ph2.uuid}


def test_search_by_date_range():
    db = make_db()
    ph = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.insert_photo(ph)

    in_range = db.search(
        start=datetime(2000, 1, 1, tzinfo=UTC), end=datetime(2030, 1, 1, tzinfo=UTC)
    )
    assert len(in_range) == 1

    out_of_range = db.search(
        start=datetime(2030, 1, 1, tzinfo=UTC), end=datetime(2031, 1, 1, tzinfo=UTC)
    )
    assert out_of_range == []


def test_search_by_circle():
    db = make_db()
    ph = Photo.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.insert_photo(ph)

    nearby = db.search(circle=(ph.latitude, ph.longitude, 1.0))
    assert len(nearby) == 1

    far_away = db.search(circle=(ph.latitude + 90, ph.longitude, 0.01))
    assert far_away == []
