from routing.heatmap import score_grid
from routing.plan import score_routes

CALM = {"wind": 10, "rain": 0, "snow": 0}
WINDY = {"wind": 47, "rain": 0, "snow": 0}      # Severe; No Travel when load > 30,000 lb


def route(route_id, duration_s, weathers):
    return {
        "id": route_id,
        "duration_s": duration_s,
        "checkpoints": [{"mile": i * 25.0, "weather": w} for i, w in enumerate(weathers)],
    }


def test_checkpoints_get_levels_with_load_rules():
    result = score_routes([route("A", 3600, [CALM, WINDY, CALM])], load_lbs=35000)
    labels = [cp["label"] for cp in result["routes"][0]["checkpoints"]]
    assert labels == ["Low", "No Travel", "Low"]
    assert "35,000 lb load" in result["routes"][0]["checkpoints"][1]["reason"]


def test_recommends_the_route_that_avoids_no_travel():
    fast_but_windy = route("A", 3600, [CALM, WINDY, CALM])
    slow_but_calm = route("B", 7200, [CALM, CALM, CALM])
    result = score_routes([fast_but_windy, slow_but_calm], load_lbs=35000)
    assert result["recommended_route_id"] == "B"
    assert result["recommendation_reason"].startswith("Avoids No Travel")


def test_light_load_makes_same_wind_only_severe():
    result = score_routes([route("A", 3600, [CALM, WINDY, CALM])], load_lbs=20000)
    assert result["routes"][0]["checkpoints"][1]["label"] == "Severe"


def test_score_grid_uses_same_rules_for_every_hour():
    series = [{"wind": [10, 47, 60], "rain": [0, 0, 0], "snow": [0, 0, 0]}]
    assert score_grid(series, load_lbs=35000) == [[0, 4, 4]]
    assert score_grid(series, load_lbs=20000) == [[0, 3, 4]]
