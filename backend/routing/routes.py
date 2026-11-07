"""Get 3 route options from OSRM, adding via-point detours if needed."""

import math

import requests

from .httpclient import describe, get_json

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
METERS_PER_MILE = 1609.344
DETOUR_MILES = [25, -25, 50, -50]   # sideways offsets to try, in order


class RoutingError(Exception):
    pass


def _osrm(coords, alternatives):
    """Call OSRM for a list of (lat, lon) waypoints."""
    path = ";".join(f"{lon},{lat}" for lat, lon in coords)
    params = {
        "alternatives": "3" if alternatives else "false",
        "overview": "full",
        "geometries": "geojson",
    }
    try:
        data = get_json(OSRM_URL + path, params=params, timeout=30)
    except requests.RequestException as exc:
        raise RoutingError(f"Routing service unavailable: {describe(exc)}") from exc

    if data.get("code") != "Ok":
        raise RoutingError("No route found between these locations")
    return [
        {
            "geometry": r["geometry"],              # GeoJSON LineString [lon, lat]
            "distance_mi": r["distance"] / METERS_PER_MILE,
            "duration_s": r["duration"],
        }
        for r in data["routes"]
    ]


def _offset_point(lat, lon, bearing_deg, miles):
    """Move a point `miles` along a compass bearing (flat-earth approximation)."""
    rad = math.radians(bearing_deg)
    dlat = (miles * math.cos(rad)) / 69.0
    dlon = (miles * math.sin(rad)) / (69.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def _is_duplicate(route, existing):
    for other in existing:
        same_distance = abs(route["distance_mi"] - other["distance_mi"]) / other["distance_mi"] < 0.03
        same_time = abs(route["duration_s"] - other["duration_s"]) / other["duration_s"] < 0.03
        if same_distance and same_time:
            return True
    return False


def get_three_routes(origin, destination):
    """Return up to 3 distinct routes, labelled A, B, C."""
    start = (origin["lat"], origin["lon"])
    end = (destination["lat"], destination["lon"])

    routes = []
    for r in _osrm([start, end], alternatives=True):
        if not _is_duplicate(r, routes):
            routes.append(r)

    # Not enough alternatives: force detours through a shifted midpoint.
    if len(routes) < 3:
        coords = routes[0]["geometry"]["coordinates"]
        mid_lon, mid_lat = coords[len(coords) // 2]
        # Direction of travel, then turn 90 degrees to go sideways.
        bearing = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
        for miles in DETOUR_MILES:
            if len(routes) >= 3:
                break
            via = _offset_point(mid_lat, mid_lon, bearing + 90, miles)
            try:
                candidate = _osrm([start, via, end], alternatives=False)[0]
            except RoutingError:
                continue
            if not _is_duplicate(candidate, routes):
                candidate["via"] = True
                routes.append(candidate)

    for label, route in zip("ABC", routes):
        route["id"] = label
    return routes[:3]