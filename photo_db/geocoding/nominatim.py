from geopy.geocoders.nominatim import Location, Nominatim

_client = None


def client() -> Nominatim:
    global _client
    if _client is None:
        _client = Nominatim(user_agent="photodb")
    return _client


def get_coords(q: str) -> tuple[float, float, float, str] | None:
    r: Location = client().geocode(q)
    return r.latitude, r.longitude, r.altitude, r.address
