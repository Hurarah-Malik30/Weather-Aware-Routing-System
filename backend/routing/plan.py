"""Plan a trip: routes -> checkpoints -> weather -> risk -> ranking."""

from .checkpoints import build_checkpoints, truck_duration_s
from .geocode import geocode
from .recommend import rank_routes, recommendation_reason, summarize_route
from .risk import checkpoint_risk
from .routes import get_three_routes
from .weather import fetch_hourly, weather_at

def simplify_line(coords, max_points=500):
    """Keep about max_points evenly spaced points (always keeps the last one)."""
    step = max(1, len(coords) // max_points)
    simplified = coords[::step]
    if simplified[-1] != coords[-1]:
        simplified.append(coords[-1])
    return simplified


def plan_trip(origin_query, destination_query, departure_utc, load_lbs, spacing_mi):
    origin = geocode(origin_query)
    destination = geocode(destination_query)
    routes = get_three_routes(origin, destination)

    # 1. Checkpoints for every route.
    for route in routes:
        route["duration_s"] = truck_duration_s(route)   # use the truck's time everywhere
        route["checkpoints"] = build_checkpoints(route, departure_utc, spacing_mi)

    # 2. One batched weather fetch for every checkpoint on every route.
    all_checkpoints = [cp for route in routes for cp in route["checkpoints"]]
    forecasts = fetch_hourly([{"lat": cp["lat"], "lon": cp["lon"]} for cp in all_checkpoints])

    # 3. Weather at each checkpoint's ETA -> risk level.
    for cp, forecast in zip(all_checkpoints, forecasts):
        weather = weather_at(forecast, cp["eta"])
        risk = checkpoint_risk(weather["wind"], weather["rain"], weather["snow"], load_lbs)
        cp.update({
            "weather": weather,
            "level": risk["level"],
            "label": risk["label"],
            "reason": risk["reason"],
            "eta": cp["eta"].isoformat(),   # datetime -> text for JSON
        })

    # 4. Summaries, ranking, recommendation.
    for route in routes:
        route["summary"] = summarize_route(route)

    ranked = rank_routes(routes)
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None

    return {
        "origin": origin,
        "destination": destination,
        "departure_utc": departure_utc.isoformat(),
        "load_lbs": load_lbs,
        "spacing_mi": spacing_mi,
        "recommended_route_id": best["id"],
        "recommendation_reason": recommendation_reason(best, runner_up),
        "routes": [
            {
                "id": r["id"],
                "distance_mi": round(r["distance_mi"], 1),
                "duration_s": round(r["duration_s"]),
                "arrival_utc": r["checkpoints"][-1]["eta"],
                "is_detour": r.get("via", False),
                "geometry": {"type": "LineString", "coordinates": simplify_line(r["geometry"]["coordinates"])},
                "checkpoints": r["checkpoints"],
                "summary": r["summary"],
            }
            for r in routes
        ],
    }