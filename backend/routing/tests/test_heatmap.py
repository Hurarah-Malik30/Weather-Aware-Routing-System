from routing.heatmap import GRID_DEG, MAX_POINTS, OFFSETS_MI, corridor_points

# A straight east-west line about 140 miles long (Kansas).
LINE = [(-100.0 + i * 0.5, 38.0) for i in range(6)]


def test_points_snap_to_grid():
    for p in corridor_points([LINE]):
        assert abs(p["lat"] / GRID_DEG - round(p["lat"] / GRID_DEG)) < 1e-6
        assert abs(p["lon"] / GRID_DEG - round(p["lon"] / GRID_DEG)) < 1e-6


def test_no_duplicate_points():
    points = corridor_points([LINE, LINE])   # the same route twice
    keys = [(p["lat"], p["lon"]) for p in points]
    assert len(keys) == len(set(keys))
    assert points == corridor_points([LINE])


def test_corridor_spreads_north_and_south_of_route():
    lats = [p["lat"] for p in corridor_points([LINE])]
    width_deg = max(OFFSETS_MI) / 69.0       # 60 miles of latitude
    assert min(lats) < 38.0 - width_deg * 0.8
    assert max(lats) > 38.0 + width_deg * 0.8


def test_point_count_is_capped():
    long_line = [(-120.0 + i * 0.3, 30.0 + i * 0.1) for i in range(200)]
    assert len(corridor_points([long_line] * 3)) <= MAX_POINTS
