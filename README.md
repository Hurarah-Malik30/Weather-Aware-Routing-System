# Weather-Aware Truck Routing

Plans a truck trip, compares **3 route options** and recommends the safest one, using the hourly weather forecast **at the time the truck will actually reach each point** on the route.

**Live demo:** _add Vercel URL_ · **API:** _add Render URL_ · **Video walkthrough:** _add Loom URL_

> The backend runs on Render's free plan, which sleeps when idle. The first request after a quiet period can take up to a minute while it wakes up; the app shows a message while this happens.

---

## Features

- **Trip input:** origin, destination, departure time, load weight (lb) and checkpoint spacing (10, 25 or 50 miles).
- **3 routes** from OSRM. If OSRM returns fewer than 3 distinct routes, extra options are created by routing through a point shifted sideways from the midpoint.
- **Checkpoints** every 10/25/50 miles along each route, each with the truck's ETA.
- **Weather at the ETA:** hourly wind, gusts, rain and snow from Open-Meteo for the hour nearest to each checkpoint's ETA.
- **Risk level per checkpoint** (Low → No Travel) from wind, rain and snow thresholds, plus load-weight rules for wind.
- **Recommendation** with a one-line reason, for example _"Fewest severe-risk miles (0 vs 50 mi)"_.
- **Map (MapLibre):** all 3 routes, checkpoints coloured by risk, popups with mile, ETA, wind, gusts, rain, snow and the reason for the level.
- **Weather heatmap with a 0–48 hour slider and play button:** risk (or wind) across a corridor around all 3 routes, plus a marker showing where the truck is at that hour.

## Risk rules

A value exactly on a boundary goes up to the higher level.

| Level | Wind (mph) | Rain (in/hr) | Snow (in/hr) |
| --- | --- | --- | --- |
| Low | under 25 | under 0.10 | under 0.5 |
| Moderate | 25 to under 35 | 0.10 to under 0.25 | 0.5 to under 1.0 |
| High | 35 to under 45 | 0.25 to under 0.50 | 1.0 to under 2.0 |
| Severe | 45 to under 55 | 0.50 to 1.00 | 2.0 to 3.0 |
| No Travel | 55 or more | over 1.00 | over 3.0 |

**Load rules (applied to wind):**

- Wind ≥ 55 mph → No Travel for any load.
- Wind 45 to under 55 mph and load over 30,000 lb → No Travel.
- Wind 35 to under 45 mph and load over 40,000 lb → at least Severe.

A checkpoint's level is the **highest** of its wind (after load rules), rain and snow levels.

## Recommendation order

Routes are ranked by, in order:

1. Fewest **No Travel** miles _(added by me, see assumptions)_
2. Fewest **Severe** miles
3. Fewest **High** miles
4. Lowest **average risk** (mile-weighted, 0–4)
5. Shortest **drive time**

Miles at a level = distance from a checkpoint to the next one, counted at that checkpoint's level.

## Assumptions and decisions

- **No Travel ranked first.** The spec's order starts at Severe; a route crossing No Travel conditions should never beat one that doesn't, so No Travel miles are compared first. If every route crosses No Travel, the app warns the user to try a later departure.
- **Truck speed.** OSRM uses a car profile, so drive time is `max(OSRM time, distance ÷ 60 mph)`. ETAs along the route are spread in proportion to distance.
- **Forecast hour.** Each checkpoint uses the forecast hour nearest to its ETA. Wind is Open-Meteo's 10 m wind speed. Gusts are shown but not scored, because the rules are defined on wind speed.
- **Departure window.** Departure must be within the next 4 days so the whole trip and the 48-hour heatmap stay inside the forecast.
- **Heatmap corridor.** Points are placed up to 60 miles either side of each route every ~25 miles, snapped to a 0.3° grid (~20 miles) so overlapping routes share points, and capped at 600 points. The heatmap uses the same risk function and load rules as the checkpoints.
- **No invented data.** If a weather or routing service fails, the API returns an error instead of guessing. Calls to the free services are retried twice (after 1 s and 2 s) on timeouts, 429 and 5xx responses.

## How it works

```
React form ──POST /api/plan/──► geocode (Nominatim)
                                 → 3 routes (OSRM)
                                 → checkpoints + ETAs
                                 → one batched weather request (Open-Meteo)
                                 → risk per checkpoint → summaries → ranking
          ◄── routes, checkpoints, summaries, recommendation

React map ──POST /api/heatmap/──► corridor grid around the routes
                                   → batched forecasts → risk for hours 0–48
          ◄── grid points with 49 hourly levels
              (moving the slider only calls map setData(); no new requests)
```

## Tech stack

| Part | Tools |
| --- | --- |
| Backend | Python, Django, Django REST Framework, django-cors-headers, requests, gunicorn |
| Frontend | React, Vite, MapLibre GL, Tailwind CSS, lucide-react |
| Data | OSRM (routes), Open-Meteo (weather), Nominatim / OpenStreetMap (geocoding), OpenFreeMap (map tiles) |
| Tests | pytest, pytest-django |
| Hosting | Render (API), Vercel (frontend) |

No API keys are needed.

## API

### `POST /api/plan/`

```json
{
  "origin": "Seattle, WA",
  "destination": "Spokane, WA",
  "departure_utc": "2026-11-08T05:00:00Z",
  "load_lbs": 35000,
  "spacing_mi": 10
}
```

Returns `recommended_route_id`, `recommendation_reason` and `routes[]`. Each route has `distance_mi`, `duration_s`, `arrival_utc`, `geometry`, `checkpoints[]` (mile, lat, lon, eta, weather, level, label, reason) and a `summary` (miles per level, average risk).

Errors: `400` for invalid input or an unknown place; `502` when a routing or weather service fails.

### `POST /api/heatmap/`

```json
{ "departure_utc": "...", "load_lbs": 35000, "paths": [[[lon, lat], ...], ...] }
```

Returns `start_utc`, `hours` (up to 49) and `points[]`, each with `lat`, `lon`, `level[hour]` and `wind[hour]`.

### `GET /api/health/`

Returns `{"ok": true}`. The frontend calls it on page load to wake the server.

## Project structure

```
backend/
  config/            Django settings and root URLs
  routing/
    risk.py          thresholds, load rules, checkpoint risk
    recommend.py     route summaries, ranking, recommendation reason
    geocode.py       place name -> coordinates (Nominatim)
    routes.py        3 route options (OSRM + detours)
    checkpoints.py   checkpoints every N miles with ETAs
    weather.py       batched hourly forecasts (Open-Meteo)
    plan.py          the full /plan pipeline
    heatmap.py       corridor grid and hourly risk
    httpclient.py    GET with retries for the free APIs
    views.py         input validation and endpoints
    tests/           unit tests
frontend/src/
  api.js             calls to the backend
  App.jsx            page layout and state
  components/        TripForm, RouteCards, RouteMap, WeatherPanel
  lib/               risk colours/formatting, heatmap and truck-position helpers
```

## Run locally

**Backend** (Python 3.12+):

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver     # http://127.0.0.1:8000
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
cp .env.example .env           # VITE_API_URL=http://127.0.0.1:8000
npm run dev                    # http://localhost:5173
```

**Tests:**

```bash
cd backend
pytest -q
```

The tests cover every risk threshold and boundary, the load rules, the ranking order and reasons, the heatmap grid and the retry logic.

## Deployment

| | Settings |
| --- | --- |
| **Render** (backend) | Root `backend`, build `pip install -r requirements.txt`, start `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`. Env: `DJANGO_SECRET_KEY`, `CORS_ALLOWED_ORIGINS` (the Vercel URL). `DEBUG` is off automatically on Render. |
| **Vercel** (frontend) | Root `frontend`, framework Vite. Env: `VITE_API_URL` (the Render URL). |

## Known limitations

- OSRM's public demo server uses a car profile and has no truck restrictions (height, weight, hazmat). It can also be slow or briefly unavailable.
- Wind direction is not considered (a crosswind is more dangerous than a headwind), and neither are visibility or ice.
- Driver rest breaks and hours-of-service rules are not modelled.
- Forecast accuracy drops further ahead; the app limits departures to 4 days.

## Time spent

About **_X_ hours** in total (backend logic and tests, frontend and map, heatmap, deployment and documentation).
