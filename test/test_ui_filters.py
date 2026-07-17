"""Unit tests for framework-agnostic UI display-formatting helpers (no Qt
required, so these run in the default test suite rather than under the
``gui`` marker)."""

from datetime import datetime

import pytest

from photo_db.ui.filters import month_label, mpixel, taken_date, trim_path


def test_trim_path_short_passthrough():
    assert trim_path("short/path.jpg") == "short/path.jpg"


def test_trim_path_long_is_shortened():
    long_path = "/a/" + "b" * 100 + "/photo.jpg"
    trimmed = trim_path(long_path)
    assert len(trimmed) < len(long_path)
    assert trimmed.startswith("/a/")
    assert trimmed.endswith("photo.jpg")
    assert ".." in trimmed


def test_trim_path_empty():
    assert trim_path("") == ""


def test_trim_path_rejects_non_string():
    with pytest.raises(ValueError):
        trim_path(123)  # type: ignore[arg-type]


def test_mpixel_small_and_large():
    assert mpixel(1024 * 1024 * 2) == "2.0 MP"
    assert mpixel(1024 * 1024 * 12) == "12 MP"


def test_taken_date_format():
    dt = datetime(2024, 3, 5, 13, 45, 30)
    assert taken_date(dt) == "2024-03-05 13:45:30"


def test_month_label_format():
    label = month_label(2024, 3)
    assert label.startswith("2024-03")
    assert "March" in label
