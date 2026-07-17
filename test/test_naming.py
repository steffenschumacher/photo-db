"""Tests for the filename/foldering scheme (Photo.db_path/filename).

Spec (clarified with the project owner): year/month folders (zero-padded),
filenames use a fixed-width numeric prefix with no separators - day-of-month
(2 digits) + hour (2) + minute (2) + second (2) + millisecond (3) - so that
files sort chronologically within a month while remaining unique.
"""

from base64 import b64encode
from datetime import UTC, datetime

import numpy as np

from photo_db.photo import Photo

_VALID_HASH = b64encode(np.zeros((70, 70), dtype=bool).tobytes()).decode("utf-8")


def make_photo(date: datetime, uuid="abcd1234-0000-0000-0000-00000000abcd") -> Photo:
    return Photo(
        uuid=uuid,
        camera="Test Camera",
        date=date,
        latitude=1.0,
        longitude=2.0,
        altitude=3.0,
        width=100,
        height=100,
        hash=_VALID_HASH,
        extension="jpg",
        scanned=datetime.now(UTC),
    )


def test_db_path_zero_pads_month():
    ph = make_photo(datetime(2024, 3, 31, 14, 5, 22, 123000, tzinfo=UTC))
    year, month, _filename = ph.db_path().split("/")
    assert year == "2024"
    assert month == "03"


def test_filename_is_fixed_width_numeric_prefix_no_separators():
    ph = make_photo(datetime(2024, 3, 31, 14, 5, 22, 123000, tzinfo=UTC))
    filename = ph.filename()
    prefix = filename.split("_")[0]
    assert prefix == "31140522123"
    assert filename == f"31140522123_{ph.uuid[-4:]}.jpg".lower()


def test_filenames_sort_chronologically_within_a_month():
    earlier = make_photo(datetime(2024, 3, 1, 8, 0, 0, 0, tzinfo=UTC), uuid="aaaa")
    later = make_photo(datetime(2024, 3, 15, 23, 59, 59, 999000, tzinfo=UTC), uuid="bbbb")
    assert sorted([later.filename(), earlier.filename()]) == [
        earlier.filename(),
        later.filename(),
    ]
