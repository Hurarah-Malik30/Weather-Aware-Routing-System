from routing.risk import LEVEL_NAMES, NO_TRAVEL, SEVERE, HIGH

def summarize_route(route):
    checkpoints = route["checkpoints"]
    miles_by_level = [0.0] * 5
    weighted_total = 0.0
    total_miles = 0.0
    for i, cp in enumerate(checkpoints):
        if i+1 < len(checkpoints):
            segment = checkpoints[i+1]["mile"] - cp["mile"]
        else:
            segment = 0
        level = cp["level"]
        miles_by_level[level] += segment
        weighted_total += segment * level
        total_miles += segment
        
    if total_miles == 0:
        avg_risk = 0
    else:
        avg_risk = weighted_total/total_miles
        
    return {
        "miles_by_level": {LEVEL_NAMES[i]: round(m, 1) for i, m in enumerate(miles_by_level)},
        "no_travel_miles": round(miles_by_level[NO_TRAVEL], 1),
        "severe_miles": round(miles_by_level[SEVERE], 1),
        "high_miles": round(miles_by_level[HIGH], 1),
        "avg_risk": round(avg_risk, 2),
        "has_no_travel": miles_by_level[NO_TRAVEL] > 0,
    }

def rank_routes(routes):
    def key(route):
        s = route["summary"]
        return(
            s["no_travel_miles"],
            s["severe_miles"],
            s["high_miles"],
            s["avg_risk"],
            route["duration_s"]
        )
    return sorted(routes, key=key)
            
def recommendation_reason(best, runner_up):
    """One sentence explaining why `best` beat `runner_up`, using the same
    rule order as rank_routes()."""
    if runner_up is None:
        reason = "Only one route available"
    else:
        b, r = best["summary"], runner_up["summary"]
        rules = [
            ("no_travel_miles", "Avoids No Travel conditions", "mi"),
            ("severe_miles", "Fewest severe-risk miles", "mi"),
            ("high_miles", "Fewest high-risk miles", "mi"),
            ("avg_risk", "Lowest average risk", ""),
        ]
        reason = None
        for field, text, unit in rules:
            if b[field] < r[field]:
                reason = f"{text} ({b[field]} vs {r[field]} {unit})".replace(" )", ")")
                break
        if reason is None:
            hours_b = best["duration_s"] / 3600
            hours_r = runner_up["duration_s"] / 3600
            reason = f"Fastest of equally safe routes ({hours_b:.1f} h vs {hours_r:.1f} h)"

    if best["summary"]["has_no_travel"]:
        reason += ". Warning: no route is safe to depart now, try a later departure time"
    return reason