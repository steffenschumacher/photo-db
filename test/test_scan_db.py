"""Regression tests for photo_db.db.scanner.ScanDB.

Covers the same class of bugs fixed in StoreDB (trailing-paren SQL syntax
errors, next(cur) raising StopIteration instead of returning None for
not-found rows, unparameterized SQL).
"""

from datetime import UTC, datetime

from photo_db.db.scanner import ScanDB
from photo_db.photo import LocalPhoto

from .conftest import STATIC_DIR


def test_upsert_and_get_photo():
    db = ScanDB()
    ph = LocalPhoto.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.upsert_photo(ph)

    fetched = db.get_photo(ph.uuid)
    assert fetched is not None
    assert fetched.uuid == ph.uuid


def test_get_photo_not_found_returns_none():
    db = ScanDB()
    assert db.get_photo("does-not-exist") is None


def test_lookup_hash_not_found_returns_none():
    db = ScanDB()
    assert db.lookup_hash("does-not-exist") is None


def test_lookup_hash_found():
    db = ScanDB()
    ph = LocalPhoto.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.upsert_photo(ph)
    assert db.lookup_hash(ph.hash) == ph.uuid


def test_upsert_replaces_existing():
    db = ScanDB()
    ph = LocalPhoto.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.upsert_photo(ph)
    ph.status = "uploaded"
    db.upsert_photo(ph)

    fetched = db.get_photo(ph.uuid)
    assert fetched.status == "uploaded"


def test_search_all_and_by_date():
    db = ScanDB()
    ph = LocalPhoto.from_file(str(STATIC_DIR / "08-190641-4631.jpeg"))
    db.upsert_photo(ph)

    assert len(db.search()) == 1
    assert len(db.search(start=datetime(2000, 1, 1, tzinfo=UTC))) == 1
    assert len(db.search(start=datetime(2030, 1, 1, tzinfo=UTC))) == 0
