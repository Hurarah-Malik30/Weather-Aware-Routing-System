// The full trip-planning flow. The backend does routing and scoring; the browser
// fetches the weather in between (see lib/weather.js for why).
import { heatmapPoints, prepareRoutes, scoreHeatmap, scoreRoutes } from '../api';
import { fetchForecasts, hourIndex, weatherAt } from './weather';

const HEATMAP_HOURS = 49; // slider positions 0..48

export async function planTrip(form) {
  // 1. Backend: geocode, 3 routes, checkpoints with ETAs.
  const prepared = await prepareRoutes(form);

  // 2. Browser: forecast at every checkpoint, at the hour the truck gets there.
  const checkpoints = prepared.routes.flatMap((r) => r.checkpoints);
  const forecasts = await fetchForecasts(checkpoints);
  checkpoints.forEach((cp, i) => {
    cp.weather = weatherAt(forecasts[i], Date.parse(cp.eta));
  });

  // 3. Backend: risk per checkpoint, summaries, ranking.
  const scored = await scoreRoutes(form.loadLbs, prepared.routes);

  return {
    ...prepared,
    load_lbs: form.loadLbs,
    recommended_route_id: scored.recommended_route_id,
    recommendation_reason: scored.recommendation_reason,
    routes: prepared.routes.map((route, r) => ({
      ...route,
      summary: scored.routes[r].summary,
      checkpoints: route.checkpoints.map((cp, c) => ({ ...cp, ...scored.routes[r].checkpoints[c] })),
    })),
  };
}

// Weather grid around all 3 routes for hours 0-48 after departure.
export async function fetchHeatmap(plan) {
  // Checkpoints are a light outline of each route (one point every 10-50 miles).
  const paths = plan.routes.map((r) => r.checkpoints.map((cp) => [cp.lon, cp.lat]));
  const { points } = await heatmapPoints(paths);

  const start = new Date(plan.departure_utc);
  start.setUTCMinutes(0, 0, 0);
  const forecasts = await fetchForecasts(points);

  const first = hourIndex(forecasts[0], start.getTime());
  if (first < 0) throw new Error('No forecast available for the departure hour.');
  const hours = Math.min(HEATMAP_HOURS, forecasts[0].times.length - first);
  const series = forecasts.map((f) => ({
    wind: f.wind.slice(first, first + hours),
    rain: f.rain.slice(first, first + hours),
    snow: f.snow.slice(first, first + hours),
  }));

  const { levels } = await scoreHeatmap(plan.load_lbs, series);

  return {
    start_utc: start.toISOString(),
    hours,
    points: points.map((p, i) => ({ ...p, level: levels[i], wind: series[i].wind.map(Math.round) })),
  };
}
