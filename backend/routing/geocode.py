"""Place name -> coordinates, using OpenStreetMap's Nominatim, with Photon as a backup.

Both are free and keyless. Render's free plan shares its outgoing IP with other
apps, so Nominatim sometimes rate-limits us; then we ask Photon (komoot), a
separate service built on the same OpenStreetMap data.
"""

import requests

from .httpclient import describe, get_json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
# Nominatim's usage policy asks for an app name and a contact email.
USER_AGENT = "WeatherTruckRouter/1.0 (m.hurarah30@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}

_cache = {}


class GeocodeError(Exception):
    pass


def _nominatim(query):
    results = get_json(NOMINATIM_URL, params={"q": query, "format": "json", "limit": 1}, headers=HEADERS, timeout=15)
    if not results:
        return None
    best = results[0]
    return {"lat": float(best["lat"]), "lon": float(best["lon"]), "name": best["display_name"]}


def _photon(query):
    data = get_json(PHOTON_URL, params={"q": query, "limit": 1}, headers=HEADERS, timeout=15)
    features = data.get("features") or []
    if not features:
        return None
    lon, lat = features[0]["geometry"]["coordinates"]        # GeoJSON order: lon, lat
    props = features[0].get("properties", {})
    name = ", ".join(p for p in (props.get("name"), props.get("state"), props.get("country")) if p)
    return {"lat": float(lat), "lon": float(lon), "name": name or query}


def geocode(query):
    """Return {"lat", "lon", "name"} for a place name."""
    key = query.strip().lower()
    if key in _cache:
        return _cache[key]

    try:
        place = _nominatim(query)
    except requests.RequestException as first_error:
        # Nominatim is down or rate-limited: try the backup service.
        try:
            place = _photon(query)
        except requests.RequestException:
            raise GeocodeError(f"Geocoding service unavailable: {describe(first_error)}") from first_error

    if place is None:
        raise GeocodeError(f"Could not find location: {query}")

    _cache[key] = place
    return place