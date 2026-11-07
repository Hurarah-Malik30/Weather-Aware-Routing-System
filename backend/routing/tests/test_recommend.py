from routing.recommend import summarize_route, rank_routes, recommendation_reason


def make_route(route_id, hours, no_travel=0, severe=0, high=0, avg=0.0):
    """Build a fake route with a ready-made summary (for ranking tests)."""
    return {
        "id": route_id,
        "duration_s": hours * 3600,
        "summary": {
            "no_travel_miles": no_travel,
            "severe_miles": severe,
            "high_miles": high,
            "avg_risk": avg,
            "has_no_travel": no_travel > 0,
        },
    }


def test_segment_miles_add_up_and_average_is_weighted():
    route = {
        "id": "A",
        "duration_s": 3600,
        "checkpoints": [
            {"mile": 0, "level": 0},   # Low,    covers 0-25
            {"mile": 25, "level": 2},  # High,   covers 25-50
            {"mile": 50, "level": 3},  # Severe, covers 50-62
            {"mile": 62, "level": 0},  # destination, covers 0
        ],
    }
    s = summarize_route(route)
    assert s["miles_by_level"]["Low"] == 25
    assert s["high_miles"] == 25
    assert s["severe_miles"] == 12
    assert s["avg_risk"] == 1.39  # (25*0 + 25*2 + 12*3) / 62


def test_fewer_severe_miles_beats_faster_route():
    fast_but_risky = make_route("A", hours=14, severe=50, avg=0.8)
    slow_but_safe = make_route("B", hours=16, severe=0, avg=0.5)
    assert rank_routes([fast_but_risky, slow_but_safe])[0]["id"] == "B"


def test_no_travel_miles_ranked_before_severe_miles():
    has_no_travel = make_route("A", hours=14, no_travel=10, severe=0)
    only_severe = make_route("B", hours=14, no_travel=0, severe=60)
    assert rank_routes([has_no_travel, only_severe])[0]["id"] == "B"


def test_travel_time_breaks_a_tie():
    slower = make_route("A", hours=15)
    faster = make_route("B", hours=14)
    assert rank_routes([slower, faster])[0]["id"] == "B"


def test_reason_explains_severe_miles():
    best = make_route("B", hours=16, severe=0)
    runner_up = make_route("A", hours=14, severe=50)
    assert recommendation_reason(best, runner_up).startswith("Fewest severe-risk miles")


def test_reason_warns_when_every_route_has_no_travel():
    best = make_route("A", hours=14, no_travel=10)
    runner_up = make_route("B", hours=14, no_travel=40)
    assert "Warning" in recommendation_reason(best, runner_up)
