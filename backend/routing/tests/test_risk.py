import routing.risk as risk


def test_wind_just_below_25_is_low():
    assert risk.wind_level(24.9) == risk.LOW


def test_wind_exactly_25_is_moderate():
    assert risk.wind_level(25) == risk.MODERATE


def test_wind_exactly_55_is_no_travel():
    assert risk.wind_level(55) == risk.NO_TRAVEL


def test_rain_exactly_025_is_high():
    assert risk.rain_level(0.25) == risk.HIGH


def test_rain_exactly_one_inch_is_severe():
    assert risk.rain_level(1.00) == risk.SEVERE


def test_rain_above_one_inch_is_no_travel():
    assert risk.rain_level(1.01) == risk.NO_TRAVEL


def test_load_rule_2_triggers_no_travel():
    assert risk.checkpoint_risk(47, 0, 0, 35000)["level"] == risk.NO_TRAVEL


def test_load_exactly_30000_does_not_trigger_rule_2():
    assert risk.checkpoint_risk(47, 0, 0, 30000)["level"] == risk.SEVERE


def test_load_rule_3_makes_severe():
    assert risk.checkpoint_risk(38, 0, 0, 42000)["level"] == risk.SEVERE


def test_worst_condition_wins():
    assert risk.checkpoint_risk(10, 0.30, 0.6, 20000)["level"] == risk.HIGH