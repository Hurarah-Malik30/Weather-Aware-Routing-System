"""Hourly weather forecasts from Open-Meteo, fetched in batches and cached.

Open-Meteo's free tier counts every location as one call (limits: 600/minute,
5,000/hour, 10,000/day), so we avoid asking for the same place twice:
- points are rounded to a ~3 mile grid, so nearby/shared points become one,
- forecasts are kept for 30 minutes, so re-planning a trip costs nothing.
"""

import time
from datetime import datetime, timezone

import requests

from .httpclient import describe, get_json

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
BATCH_SIZE = 100          # points per request (keeps URLs a safe length)
FORECAST_DAYS = 7         # covers a departure up to 4 days ahead + a long trip
SNAP_DEG = 0.05           # ~3 miles; finer than the forecast model's own grid
CACHE_TTL_S = 30 * 60     # forecasts update hourly; 30 minutes is fresh enough
CACHE_MAX = 3000          # points kept in memory per server process

_cache = {}               # (lat, lon) -> (fetched_at, forecast)


class WeatherError(Exception):
    """Raised when the weather API fails. Never invent weather instead."""


def _key(point):
    return (
        round(round(point["lat"] / SNAP_DEG) * SNAP_DEG, 4),
        round(round(point["lon"] / SNAP_DEG) * SNAP_DEG, 4),
    )


def _parse_batch(data):
    """Open-Meteo JSON -> list of forecasts (one per location)."""
    # One point -> a single object; several points -> a list of objects.
    locations = data if isinstance(data, list) else [data]
    # Every location shares the same hours, so parse the times once.
    times = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in locations[0]["hourly"]["time"]]
    return [
        {
            "times": times,
            "wind": loc["hourly"]["wind_speed_10m"],
            "gust": loc["hourly"]["wind_gusts_10m"],
            "rain": loc["hourly"]["rain"],
            "snow": loc["hourly"]["snowfall"],
        }
        for loc in locations
    ]


def _trim_cache(now):
    for key in [k for k, (fetched, _) in _cache.items() if now - fetched > CACHE_TTL_S]:
        del _cache[key]
    while len(_cache) > CACHE_MAX:
        del _cache[next(iter(_cache))]          # oldest entry first


def fetch_hourly(points):
    """Return one hourly forecast per point, in the same order as `points`.

    points: list of {"lat": float, "lon": float}
    Each result: {"times": [datetime UTC...], "wind": [...mph],
                  "gust": [...mph], "rain": [...in/hr], "snow": [...in/hr]}
    """
    now = time.monotonic()
    _trim_cache(now)

    keys = [_key(p) for p in points]
    missing = list(dict.fromkeys(k for k in keys if k not in _cache))   # unique, in order

    for start in range(0, len(missing), BATCH_SIZE):
        batch = missing[start:start + BATCH_SIZE]
        params = {
            "latitude": ",".join(f"{lat:.4f}" for lat, _ in batch),
            "longitude": ",".join(f"{lon:.4f}" for _, lon in batch),
            "hourly": "wind_speed_10m,wind_gusts_10m,rain,snowfall",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",   # rain AND snowfall in inches
            "timezone": "UTC",
            "forecast_days": FORECAST_DAYS,
        }
        try:
            data = get_json(OPEN_METEO_URL, params=params, timeout=20)
        except requests.RequestException as exc:
            raise WeatherError(f"Weather service unavailable: {describe(exc)}") from exc

        for key, forecast in zip(batch, _parse_batch(data)):
            _cache[key] = (now, forecast)

    return [_cache[k][1] for k in keys]


def weather_at(forecast, when):
    """Weather from `forecast` at the hour nearest to `when` (a UTC datetime).

    Raises WeatherError if `when` is outside the forecast range.
    """
    times = forecast["times"]
    if when < times[0] or when > times[-1]:
        raise WeatherError(f"No forecast available for {when:%Y-%m-%d %H:%M} UTC")

    # Index of the forecast hour closest to `when`.
    idx = min(range(len(times)), key=lambda i: abs(times[i] - when))

    return {
        "time": times[idx].isoformat(),
        "wind": forecast["wind"][idx] or 0.0,
        "gust": forecast["gust"][idx] or 0.0,
        "rain": forecast["rain"][idx] or 0.0,
        "snow": forecast["snow"][idx] or 0.0,
    }