from datetime import datetime, timedelta, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .geocode import GeocodeError
from .heatmap import HOURS, MAX_POINTS, corridor_points, score_grid
from .plan import prepare_routes, score_routes
from .routes import RoutingError

ALLOWED_SPACING = {10, 25, 50}
MAX_DAYS_AHEAD = 4        # forecasts are reliable for a few days only
MAX_PATH_POINTS = 1000
MAX_CHECKPOINTS = 1000    # 3,000 miles at 10-mile spacing is ~300; this is a safety cap


class InvalidInput(Exception):
    pass


def bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def bad_gateway(message):
    return Response({"error": message}, status=status.HTTP_502_BAD_GATEWAY)


def number(value, name, minimum=0.0):
    """A float >= minimum; missing weather values (None) count as 0."""
    if value is None:
        return 0.0
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise InvalidInput(f"{name} must be a number.")
    if value < minimum:
        raise InvalidInput(f"{name} must be at least {minimum}.")
    return value


def parse_load(data):
    try:
        load_lbs = float(data.get("load_lbs"))
    except (TypeError, ValueError):
        raise InvalidInput("Load weight must be a number.")
    if load_lbs <= 0 or load_lbs > 80000:
        raise InvalidInput("Load weight must be between 1 and 80,000 lb.")
    return load_lbs


def parse_departure(data):
    try:
        departure = datetime.fromisoformat(data.get("departure_utc"))
    except (TypeError, ValueError):
        raise InvalidInput("Departure time must be an ISO date-time.")
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    departure = departure.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    if departure < now - timedelta(minutes=15):
        raise InvalidInput("Departure time must be in the future.")
    if departure > now + timedelta(days=MAX_DAYS_AHEAD):
        raise InvalidInput(f"Departure must be within {MAX_DAYS_AHEAD} days (forecast limit).")
    return departure


def parse_paths(data):
    """[[ [lon, lat], ... ], ...] -> list of lists of (lon, lat) floats."""
    paths = data.get("paths")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 3:
        raise InvalidInput("Send 1 to 3 route paths.")
    try:
        parsed = [[(float(lon), float(lat)) for lon, lat in path] for path in paths]
    except (TypeError, ValueError):
        raise InvalidInput("Each path must be a list of [lon, lat] pairs.")
    if any(len(p) < 2 or len(p) > MAX_PATH_POINTS for p in parsed):
        raise InvalidInput(f"Each path needs 2 to {MAX_PATH_POINTS} points.")
    return parsed


def parse_scored_routes(data):
    """Routes with the weather the browser fetched for each checkpoint."""
    routes = data.get("routes")
    if not isinstance(routes, list) or not 1 <= len(routes) <= 3:
        raise InvalidInput("Send 1 to 3 routes.")
    parsed = []
    for route in routes:
        checkpoints = route.get("checkpoints") if isinstance(route, dict) else None
        if not isinstance(checkpoints, list) or not 1 <= len(checkpoints) <= MAX_CHECKPOINTS:
            raise InvalidInput(f"Each route needs 1 to {MAX_CHECKPOINTS} checkpoints.")
        cps = []
        for cp in checkpoints:
            weather = cp.get("weather") if isinstance(cp, dict) else None
            if not isinstance(weather, dict):
                raise InvalidInput("Each checkpoint needs its weather.")
            cps.append({
                "mile": number(cp.get("mile"), "Checkpoint mile"),
                "weather": {
                    "wind": number(weather.get("wind"), "Wind"),
                    "rain": number(weather.get("rain"), "Rain"),
                    "snow": number(weather.get("snow"), "Snow"),
                },
            })
        parsed.append({
            "id": str(route.get("id", ""))[:5],
            "duration_s": number(route.get("duration_s"), "Route duration"),
            "checkpoints": cps,
        })
    return parsed


def parse_grid(data):
    """Hourly wind/rain/snow for each heatmap point, as fetched by the browser."""
    series = data.get("points")
    if not isinstance(series, list) or not 1 <= len(series) <= MAX_POINTS:
        raise InvalidInput(f"Send 1 to {MAX_POINTS} points.")
    parsed = []
    for point in series:
        hours = {}
        for key, name in (("wind", "Wind"), ("rain", "Rain"), ("snow", "Snow")):
            values = point.get(key) if isinstance(point, dict) else None
            if not isinstance(values, list) or len(values) > HOURS:
                raise InvalidInput(f"Each point needs up to {HOURS} hourly {key} values.")
            hours[key] = [number(v, name) for v in values]
        parsed.append(hours)
    return parsed


class ApiRootView(APIView):
    """What a visitor sees at the API's home page: what this service is and its endpoints."""

    def get(self, request):
        return Response({
            "service": "Weather-Aware Truck Routing API",
            "frontend": "https://weather-aware-routing-system.vercel.app/",
            "endpoints": {
                "GET /api/health/": "Health check, returns {\"ok\": true}",
                "POST /api/routes/": "3 routes with checkpoints and ETAs for a trip",
                "POST /api/score/": "Risk per checkpoint, route summaries and the recommendation",
                "POST /api/heatmap/points/": "Grid points around the routes for the weather heatmap",
                "POST /api/heatmap/": "Risk level for every heatmap point and hour",
            },
            "note": "Weather is fetched from Open-Meteo by the browser, so each user uses their own free quota.",
        })


class HealthView(APIView):
    """Cheap endpoint the frontend calls on page load to wake the free Render server."""

    def get(self, request):
        return Response({"ok": True})


class RoutesView(APIView):
    def post(self, request):
        data = request.data

        origin = (data.get("origin") or "").strip()
        destination = (data.get("destination") or "").strip()
        if not origin or not destination:
            return bad_request("Origin and destination are required.")

        try:
            spacing = int(data.get("spacing_mi", 25))
        except (TypeError, ValueError):
            spacing = None
        if spacing not in ALLOWED_SPACING:
            return bad_request("Checkpoint spacing must be 10, 25 or 50 miles.")

        try:
            departure = parse_departure(data)
        except InvalidInput as exc:
            return bad_request(str(exc))

        try:
            result = prepare_routes(origin, destination, departure, spacing)
        except GeocodeError as exc:
            return bad_request(str(exc))
        except RoutingError as exc:
            return bad_gateway(str(exc))

        return Response(result)


class ScoreView(APIView):
    def post(self, request):
        try:
            load_lbs = parse_load(request.data)
            routes = parse_scored_routes(request.data)
        except InvalidInput as exc:
            return bad_request(str(exc))
        return Response(score_routes(routes, load_lbs))


class HeatmapPointsView(APIView):
    def post(self, request):
        try:
            paths = parse_paths(request.data)
        except InvalidInput as exc:
            return bad_request(str(exc))
        return Response({"points": corridor_points(paths)})


class HeatmapView(APIView):
    def post(self, request):
        try:
            load_lbs = parse_load(request.data)
            series = parse_grid(request.data)
        except InvalidInput as exc:
            return bad_request(str(exc))
        return Response({"levels": score_grid(series, load_lbs)})
