"""Weather heatmap: a grid of points around the routes, with risk for every hour 0-48."""

import math

from .checkpoints import haversine_miles
from .risk import checkpoint_risk
from .routes import _offset_point
from .weather import WeatherError, fetch_hourly

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


def build_heatmap(paths, departure_utc, load_lbs):
    """Risk level and wind speed at every corridor point for each hour from departure."""
    points = corridor_points(paths)
    if not points:
        return {"start_utc": None, "hours": 0, "points": []}

    start = departure_utc.replace(minute=0, second=0, microsecond=0)
    forecasts = fetch_hourly(points)

    times = forecasts[0]["times"]
    if start not in times:
        raise WeatherError("No forecast available for the departure hour")
    first = times.index(start)
    count = min(HOURS, len(times) - first)

    for point, forecast in zip(points, forecasts):
        levels, winds = [], []
        for i in range(first, first + count):
            wind = forecast["wind"][i] or 0.0
            rain = forecast["rain"][i] or 0.0
            snow = forecast["snow"][i] or 0.0
            levels.append(checkpoint_risk(wind, rain, snow, load_lbs)["level"])
            winds.append(round(wind))
        point["level"] = levels
        point["wind"] = winds

    return {"start_utc": start.isoformat(), "hours": count, "load_lbs": load_lbs, "points": points}
