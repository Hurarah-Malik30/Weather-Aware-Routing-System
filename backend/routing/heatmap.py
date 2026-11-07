"""Weather heatmap: grid points around the routes, and risk for each hour 0-48.

The server picks the points (corridor_points); the browser fetches their hourly
forecast from Open-Meteo; the server scores it (score_grid) with the same
checkpoint_risk() and load rules used for the routes.
"""

import math

from .checkpoints import haversine_miles
from .risk import checkpoint_risk
from .routes import _offset_point

HOURS = 49                          # slider positions 0..48
GRID_DEG = 0.4                      # snap points to a 0.4 degree grid (~25 miles)
SPINE_STEP_MI = 30                  # one cross-section of the corridor every 30 miles
OFFSETS_MI = (-50, -25, 0, 25, 50)  # corridor width: 50 miles each side of the route
MAX_POINTS = 250                    # each point is one call on Open-Meteo's free tier


def _bearing(lat1, lon1, lat2, lon2):
    """Compass bearing in degrees from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(x, y))


def corridor_points(paths):
    """Grid points covering a band around each path.

    paths: list of [(lon, lat), ...] lines (one per route).
    Returns [{"lat", "lon"}] snapped to the grid, with no duplicates.
    """
    seen, points = set(), []
    for path in paths:
        last = None
        for i, (lon, lat) in enumerate(path):
            is_last = i == len(path) - 1
            if last and not is_last and haversine_miles(last[0], last[1], lat, lon) < SPINE_STEP_MI:
                continue
            last = (lat, lon)

            # Direction of travel here; the corridor runs at right angles to it.
            prev_lon, prev_lat = path[max(i - 1, 0)]
            next_lon, next_lat = path[min(i + 1, len(path) - 1)]
            bearing = _bearing(prev_lat, prev_lon, next_lat, next_lon)

            for offset in OFFSETS_MI:
                plat, plon = _offset_point(lat, lon, bearing + 90, offset)
                key = (round(plat / GRID_DEG), round(plon / GRID_DEG))
                if key not in seen:
                    seen.add(key)
                    points.append({"lat": round(key[0] * GRID_DEG, 4), "lon": round(key[1] * GRID_DEG, 4)})

    # Too many points: keep an even spread rather than cutting off the end.
    step = math.ceil(len(points) / MAX_POINTS)
    return points[::step]


def score_grid(series, load_lbs):
    """series: [{"wind": [...], "rain": [...], "snow": [...]}] hourly values per point.

    Returns the risk level for every point and hour: [[level, ...], ...].
    """
    return [
        [checkpoint_risk(w, r, s, load_lbs)["level"] for w, r, s in zip(p["wind"], p["rain"], p["snow"])]
        for p in series
    ]
