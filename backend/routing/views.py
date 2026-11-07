from datetime import datetime, timedelta, timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .geocode import GeocodeError
from .heatmap import build_heatmap
from .plan import plan_trip
from .routes import RoutingError
from .weather import WeatherError

ALLOWED_SPACING = {10, 25, 50}
MAX_DAYS_AHEAD = 4   # forecasts are reliable for a few days only
MAX_PATH_POINTS = 1000


class InvalidInput(Exception):
    pass


def bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def bad_gateway(message):
    return Response({"error": message}, status=status.HTTP_502_BAD_GATEWAY)


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


class ApiRootView(APIView):
    """What a visitor sees at the API's home page: what this service is and its endpoints."""

    def get(self, request):
        return Response({
            "service": "Weather-Aware Truck Routing API",
            "frontend": "https://weather-aware-routing-system.vercel.app/",
            "endpoints": {
                "GET /api/health/": "Health check, returns {\"ok\": true}",
                "POST /api/plan/": "Plan a trip: 3 routes, checkpoint weather and risk, recommendation",
                "POST /api/heatmap/": "Hourly risk grid around the routes for hours 0-48",
            },
        })


class HealthView(APIView):
    """Cheap endpoint the frontend calls on page load to wake the free Render server."""

    def get(self, request):
        return Response({"ok": True})


class PlanView(APIView):
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
            load_lbs = parse_load(data)
            departure = parse_departure(data)
        except InvalidInput as exc:
            return bad_request(str(exc))

        try:
            result = plan_trip(origin, destination, departure, load_lbs, spacing)
        except GeocodeError as exc:
            return bad_request(str(exc))
        except (RoutingError, WeatherError) as exc:
            return bad_gateway(str(exc))

        return Response(result)


class HeatmapView(APIView):
    def post(self, request):
        data = request.data
        try:
            paths = parse_paths(data)
            load_lbs = parse_load(data)
            departure = parse_departure(data)
        except InvalidInput as exc:
            return bad_request(str(exc))

        try:
            result = build_heatmap(paths, departure, load_lbs)
        except WeatherError as exc:
            return bad_gateway(str(exc))

        return Response(result)
