import pytest

from photo_db.geocoding import get_coords

from .conftest import nearly_equals


@pytest.mark.network
def test_get_coords():
    lat, lon, alt, addr = get_coords("ternevej 11, 8870, dk")
    assert nearly_equals(lat, 56.43538804633685)
    assert nearly_equals(lon, 9.950722069014743)
    assert nearly_equals(alt, 4.0, 10)
