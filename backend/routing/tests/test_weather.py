import pytest

from routing import weather


def fake_response(n_locations):
    hourly = {
        "time": ["2026-11-08T00:00", "2026-11-08T01:00"],
        "wind_speed_10m": [10, 12],
        "wind_gusts_10m": [15, 18],
        "rain": [0.0, 0.1],
        "snowfall": [0.0, 0.0],
    }
    locations = [{"hourly": hourly} for _ in range(n_locations)]
    return locations if n_locations > 1 else locations[0]


@pytest.fixture
def api(monkeypatch):
    """Count the locations requested from Open-Meteo, with an empty cache."""
    monkeypatch.setattr(weather, "_cache", {})
    requested = []

    def fake_get_json(url, params=None, **kwargs):
        n = len(params["latitude"].split(","))
        requested.append(n)
        return fake_response(n)

    monkeypatch.setattr(weather, "get_json", fake_get_json)
    return requested


def test_same_place_is_requested_once(api):
    seattle = {"lat": 47.6062, "lon": -122.3321}
    nearby = {"lat": 47.6071, "lon": -122.3330}      # ~0.1 mile away, same grid cell
    results = weather.fetch_hourly([seattle, nearby, seattle])
    assert api == [1]
    assert len(results) == 3


def test_second_call_uses_cache(api):
    points = [{"lat": 40.0, "lon": -100.0}, {"lat": 41.0, "lon": -101.0}]
    weather.fetch_hourly(points)
    weather.fetch_hourly(points)
    assert api == [2]


def test_results_keep_input_order(api):
    points = [{"lat": 40.0, "lon": -100.0}, {"lat": 41.0, "lon": -101.0}]
    a, b = weather.fetch_hourly(points)
    assert a["wind"] == [10, 12] and b["times"][1].hour == 1


def test_large_requests_are_batched(api):
    points = [{"lat": 30 + i * 0.1, "lon": -100.0} for i in range(250)]
    weather.fetch_hourly(points)
    assert api == [100, 100, 50]
