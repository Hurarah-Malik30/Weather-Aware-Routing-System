"""Plan a trip in two halves, with the weather fetched by the browser in between.

1. prepare_routes():  place names -> 3 routes -> checkpoints with ETAs.
   (The browser then fetches the forecast at each checkpoint from Open-Meteo,
   so every user spends their own free quota instead of the server's shared IP.)
2. score_routes():    checkpoint weather -> risk levels -> summaries -> ranking.
"""

from .checkpoints import build_checkpoints, truck_duration_s
from .geocode import geocode
from .recommend import rank_routes, recommendation_reason, summarize_route
from .risk import checkpoint_risk
from .routes import get_three_routes


def simplify_line(coords, max_points=500):
    """Keep about max_points evenly spaced points (always keeps the last one)."""
    step = max(1, len(coords) // max_points)
    simplified = coords[::step]
    if simplified[-1] != coords[-1]:
        simplified.append(coords[-1])
    return simplified


def prepare_routes(origin_query, destination_query, departure_utc, spacing_mi):
    origin = geocode(origin_query)
    destination = geocode(destination_query)
    routes = get_three_routes(origin, destination)

    prepared = []
    for r in routes:
        duration_s = truck_duration_s(r)            # use the truck's time everywhere
        r["duration_s"] = duration_s
        checkpoints = build_checkpoints(r, departure_utc, spacing_mi)
        prepared.append({
            "id": r["id"],
            "distance_mi": round(r["distance_mi"], 1),
            "duration_s": round(duration_s),
            "arrival_utc": checkpoints[-1]["eta"].isoformat(),
            "is_detour": r.get("via", False),
            "geometry": {"type": "LineString", "coordinates": simplify_line(r["geometry"]["coordinates"])},
            "checkpoints": [
                {"mile": cp["mile"], "lat": cp["lat"], "lon": cp["lon"], "eta": cp["eta"].isoformat()}
                for cp in checkpoints
            ],
        })

    return {
        "origin": origin,
        "destination": destination,
        "departure_utc": departure_utc.isoformat(),
        "spacing_mi": spacing_mi,
        "routes": prepared,
    }


def score_routes(routes, load_lbs):
    """routes: [{"id", "duration_s", "checkpoints": [{"mile", "weather": {wind, rain, snow}}]}]

    Returns the risk at every checkpoint, a summary per route and the recommendation.
    """
    for route in routes:
        for cp in route["checkpoints"]:
            w = cp["weather"]
            risk = checkpoint_risk(w["wind"], w["rain"], w["snow"], load_lbs)
            cp.update({"level": risk["level"], "label": risk["label"], "reason": risk["reason"]})
        route["summary"] = summarize_route(route)

    ranked = rank_routes(routes)
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    return {
        "recommended_route_id": best["id"],
        "recommendation_reason": recommendation_reason(best, runner_up),
        "routes": [
            {
                "id": r["id"],
                "summary": r["summary"],
                "checkpoints": [
                    {"level": cp["level"], "label": cp["label"], "reason": cp["reason"]}
                    for cp in r["checkpoints"]
                ],
            }
            for r in routes
        ],
    }
