import pytest
import requests

from routing import geocode as geo


class FakeResponse:
    status_code = 429

    def json(self):
        return {}


def rate_limited():
    return requests.HTTPError("429", response=FakeResponse())


PHOTON_SEATTLE = {
    "features": [{
        "geometry": {"coordinates": [-122.33, 47.61]},
        "properties": {"name": "Seattle", "state": "Washington", "country": "United States"},
    }]
}


@pytest.fixture
def calls(monkeypatch):
    """Record which service was called; the test decides how each one answers."""
    monkeypatch.setattr(geo, "_cache", {})
    log = []
    answers = {}

    def fake_get_json(url, **kwargs):
        service = "photon" if url == geo.PHOTON_URL else "nominatim"
        log.append(service)
        answer = answers[service]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(geo, "get_json", fake_get_json)
    return log, answers


def test_uses_nominatim_when_it_works(calls):
    log, answers = calls
    answers["nominatim"] = [{"lat": "47.6", "lon": "-122.3", "display_name": "Seattle, WA"}]
    assert geo.geocode("Seattle, WA") == {"lat": 47.6, "lon": -122.3, "name": "Seattle, WA"}
    assert log == ["nominatim"]


def test_falls_back_to_photon_when_rate_limited(calls):
    log, answers = calls
    answers["nominatim"] = rate_limited()
    answers["photon"] = PHOTON_SEATTLE
    place = geo.geocode("Seattle, WA")
    assert (place["lat"], place["lon"]) == (47.61, -122.33)     # lon/lat order converted correctly
    assert place["name"] == "Seattle, Washington, United States"
    assert log == ["nominatim", "photon"]


def test_error_when_both_services_fail(calls):
    _, answers = calls
    answers["nominatim"] = rate_limited()
    answers["photon"] = requests.Timeout()
    with pytest.raises(geo.GeocodeError, match="rate limit"):
        geo.geocode("Seattle, WA")


def test_unknown_place(calls):
    _, answers = calls
    answers["nominatim"] = []
    with pytest.raises(geo.GeocodeError, match="Could not find location"):
        geo.geocode("Xyzzyville")