"""GET JSON from the free public APIs, retrying their short outages.

OSRM's demo server, Open-Meteo and Nominatim are free and sometimes time out
or answer 5xx for a moment. Retrying twice fixes most of these failures.
429 (rate limit) is NOT retried: every retry would count against the limit again.
"""

import time

import requests

RETRY_STATUSES = {500, 502, 503, 504}
ATTEMPTS = 3
BACKOFF_S = 1.0   # wait 1 s, then 2 s


def get_json(url, params=None, headers=None, timeout=20):
    """Return the JSON body, or raise requests.RequestException after the last attempt."""
    for attempt in range(ATTEMPTS):
        last = attempt == ATTEMPTS - 1
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout):
            if last:
                raise
        else:
            if response.status_code not in RETRY_STATUSES or last:
                response.raise_for_status()
                return response.json()
        time.sleep(BACKOFF_S * (attempt + 1))


def describe(exc):
    """Short, user-friendly text for a failed request (no long URLs)."""
    response = getattr(exc, "response", None)
    if response is not None and response.status_code == 429:
        return "rate limit reached on the free service, please wait a minute and try again"
    if response is not None:
        return f"HTTP {response.status_code}"
    if isinstance(exc, requests.Timeout):
        return "request timed out"
    if isinstance(exc, requests.ConnectionError):
        return "could not connect"
    return "unexpected response"
