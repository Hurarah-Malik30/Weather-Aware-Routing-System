"""GET JSON from the free public APIs, retrying their short outages.

OSRM's demo server, Open-Meteo and Nominatim are free and sometimes time out
or answer 429/5xx for a moment. Retrying twice fixes most of these failures.
"""

import time

import requests

RETRY_STATUSES = {429, 500, 502, 503, 504}
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
