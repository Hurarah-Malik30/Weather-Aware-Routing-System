"""Weather risk rules for truck routing.

Levels are numbers so they can be compared with max():
0 = Low, 1 = Moderate, 2 = High, 3 = Severe, 4 = No Travel
"""

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = 0, 1, 2, 3, 4
LEVEL_NAMES = ["Low", "Moderate", "High", "Severe", "No Travel"]


def wind_level(mph):
    """Wind speed in mph -> level. A value on a boundary goes up a level."""
    if mph >= 55:
        return NO_TRAVEL
    if mph >= 45:
        return SEVERE
    if mph >= 35:
        return HIGH
    if mph >= 25:
        return MODERATE
    return LOW


def rain_level(in_per_hr):
    """Rain in inches/hour -> level. No Travel only when MORE than 1.00."""
    if in_per_hr > 1.0:
        return NO_TRAVEL
    if in_per_hr >= 0.50:
        return SEVERE
    if in_per_hr >= 0.25:
        return HIGH
    if in_per_hr >= 0.10:
        return MODERATE
    return LOW


def snow_level(in_per_hr):
    """Snow in inches/hour -> level. No Travel only when MORE than 3.0."""
    if in_per_hr > 3.0:
        return NO_TRAVEL
    if in_per_hr >= 2.0:
        return SEVERE
    if in_per_hr >= 1.0:
        return HIGH
    if in_per_hr >= 0.5:
        return MODERATE
    return LOW


def apply_load_rules(wind_mph, base_wind_level, load_lbs):
    """Heavier loads make strong wind more dangerous.

    - >= 55 mph: No Travel for any load
    - 45-54 mph and load > 30,000 lb: No Travel
    - 35-44 mph and load > 40,000 lb: Severe
    Never lowers a level, only raises it.
    """
    if wind_mph >= 55:
        return NO_TRAVEL
    if wind_mph >= 45 and load_lbs > 30000:
        return NO_TRAVEL
    if wind_mph >= 35 and load_lbs > 40000:
        return max(base_wind_level, SEVERE)
    return base_wind_level


def checkpoint_risk(wind_mph, rain_in, snow_in, load_lbs):
    """Risk at one checkpoint.

    1. Score wind, rain and snow separately.
    2. Apply the load rules to the wind level.
    3. The checkpoint's level is the worst (highest) of the three.
    4. Explain which condition set that level.
    """
    base_wind = wind_level(wind_mph)
    wind = apply_load_rules(wind_mph, base_wind, load_lbs)
    rain = rain_level(rain_in)
    snow = snow_level(snow_in)

    level = max(wind, rain, snow)

    # Build a human-readable reason from the condition that set the level.
    if level == LOW:
        reason = "All conditions low"
    elif level == wind:
        reason = f"Wind {wind_mph:.0f} mph"
        if wind > base_wind:
            reason += f" + {load_lbs:,.0f} lb load"
    elif level == rain:
        reason = f"Rain {rain_in:.2f} in/hr"
    else:
        reason = f"Snow {snow_in:.2f} in/hr"
    reason += f" -> {LEVEL_NAMES[level]}"

    return {
        "level": level,
        "label": LEVEL_NAMES[level],
        "reason": reason,
        "wind_level": wind,
        "rain_level": rain,
        "snow_level": snow,
    }