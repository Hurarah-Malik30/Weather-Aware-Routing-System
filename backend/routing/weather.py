"""Hourly weather forecasts from Open-Meteo, fetched in batches."""

from datetime import datetime, timezone

import requests

from .httpclient import get_json

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
BATCH_SIZE = 100          # points per request (keeps URLs a safe length)
FORECAST_DAYS = 7         # covers departure up to ~2 days + a long trip


class WeatherError(Exception):
    """Raised when the weather API fails. Never invent weather instead."""


def fetch_hourly(points):
    """Return one hourly forecast per point, in the same order as `points`.

    points: list of {"lat": float, "lon": float}
    Each result: {"times": [datetime UTC...], "wind": [...mph],
                  "gust": [...mph], "rain": [...in/hr], "snow": [...in/hr]}
    """
    results = []
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        params = {
            "latitude": ",".join(f"{p['lat']:.4f}" for p in batch),
            "longitude": ",".join(f"{p['lon']:.4f}" for p in batch),
            "hourly": "wind_speed_10m,wind_gusts_10m,rain,snowfall",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",   # rain AND snowfall in inches
            "timezone": "UTC",
            "forecast_days": FORECAST_DAYS,
        }
        try:
            data = get_json(OPEN_METEO_URL, params=params, timeout=20)
        except requests.RequestException as exc:
            raise WeatherError(f"Weather service unavailable: {exc}") from exc

        # One point -> a single object; several points -> a list of objects.
        locations = data if isinstance(data, list) else [data]
        for loc in locations:
            hourly = loc["hourly"]
            results.append({
                "times": [
                    datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
                    for t in hourly["time"]
                ],
                "wind": hourly["wind_speed_10m"],
                "gust": hourly["wind_gusts_10m"],
                "rain": hourly["rain"],
                "snow": hourly["snowfall"],
            })
    return results


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