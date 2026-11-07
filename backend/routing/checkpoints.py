"""Checkpoints every N miles along a route, with the truck's ETA at each."""

import math
from datetime import timedelta

EARTH_RADIUS_MI = 3958.8
TRUCK_AVG_MPH = 60   # assumption: trucks average no more than 60 mph


def haversine_miles(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def truck_duration_s(route):
    """Car time from OSRM, but never faster than the truck's average speed."""
    return max(route["duration_s"], route["distance_mi"] / TRUCK_AVG_MPH * 3600)


def build_checkpoints(route, departure_utc, spacing_mi):
    """Return [{"mile", "lat", "lon", "eta"}] every `spacing_mi` miles."""
    coords = route["geometry"]["coordinates"]   # [[lon, lat], ...]
    total_s = truck_duration_s(route)

    # Cumulative distance at every route point.
    cumulative = [0.0]
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        cumulative.append(cumulative[-1] + haversine_miles(lat1, lon1, lat2, lon2))
    total_mi = cumulative[-1]

    # Target miles: 0, N, 2N, ... and always the destination.
    targets = [m * spacing_mi for m in range(int(total_mi // spacing_mi) + 1)]
    if total_mi - targets[-1] > 0.5:
        targets.append(total_mi)

    checkpoints = []
    j = 0
    for target in targets:
        # Move j forward until the segment [j, j+1] contains the target mile.
        while j < len(cumulative) - 2 and cumulative[j + 1] < target:
            j += 1
        seg_len = cumulative[j + 1] - cumulative[j] or 1e-9
        t = min(max((target - cumulative[j]) / seg_len, 0), 1)
        lon = coords[j][0] + t * (coords[j + 1][0] - coords[j][0])
        lat = coords[j][1] + t * (coords[j + 1][1] - coords[j][1])

        eta = departure_utc + timedelta(seconds=total_s * target / total_mi)
        checkpoints.append({"mile": round(target, 1), "lat": lat, "lon": lon, "eta": eta})

    return checkpoints