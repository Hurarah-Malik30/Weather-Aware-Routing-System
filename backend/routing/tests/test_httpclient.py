import pytest
import requests

from routing import httpclient


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._body


@pytest.fixture
def replies(monkeypatch):
    """Make requests.get return the queued replies in order; skip the sleeps."""
    queue = []

    def fake_get(*args, **kwargs):
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(httpclient.requests, "get", fake_get)
    monkeypatch.setattr(httpclient.time, "sleep", lambda s: None)
    return queue


def test_returns_json_first_time(replies):
    replies.append(FakeResponse(200, {"ok": True}))
    assert httpclient.get_json("http://x") == {"ok": True}


def test_retries_timeout_then_succeeds(replies):
    replies += [requests.Timeout(), FakeResponse(503), FakeResponse(200, {"ok": 1})]
    assert httpclient.get_json("http://x") == {"ok": 1}


def test_gives_up_after_three_attempts(replies):
    replies += [FakeResponse(503), FakeResponse(503), FakeResponse(503)]
    with pytest.raises(requests.HTTPError):
        httpclient.get_json("http://x")


@pytest.mark.parametrize("status", [400, 429])
def test_does_not_retry_client_errors_or_rate_limits(replies, status):
    replies += [FakeResponse(status), FakeResponse(200, {})]
    with pytest.raises(requests.HTTPError):
        httpclient.get_json("http://x")
    assert len(replies) == 1   # the second reply was never requested
