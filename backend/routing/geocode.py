"""Place name -> coordinates, using OpenStreetMap's Nominatim."""

import requests

from .httpclient import get_json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy asks for an app name and a contact email.
USER_AGENT = "WeatherTruckRouter/1.0 (m.hurarah30@gmail.com)"

_cache = {}


class GeocodeError(Exception):
    pass


def geocode(query):
    """Return {"lat", "lon", "name"} for a place name."""
    key = query.strip().lower()
    if key in _cache:
        return _cache[key]

    try:
        results = get_json(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise GeocodeError(f"Geocoding service unavailable: {exc}") from exc

    if not results:
        raise GeocodeError(f"Could not find location: {query}")

    place = {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "name": results[0]["display_name"],
    }
    _cache[key] = place
    return place