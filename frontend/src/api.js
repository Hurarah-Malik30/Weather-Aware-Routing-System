// All calls to the Django backend live here.
const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

async function post(path, body) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Cannot reach the server. Is the backend running?');
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.error || `Request failed (${response.status})`);
  }
  return data;
}

// The free Render server sleeps when idle; calling this on page load wakes it early.
export async function pingServer() {
  const response = await fetch(`${API_URL}/api/health/`);
  if (!response.ok) throw new Error(`Server returned ${response.status}`);
}

// 1st half of planning: 3 routes with checkpoints and ETAs (no weather yet).
export function prepareRoutes({ origin, destination, departureLocal, spacingMi }) {
  return post('/api/routes/', {
    origin,
    destination,
    // datetime-local gives local time with no zone; convert to UTC at submit time.
    departure_utc: new Date(departureLocal).toISOString(),
    spacing_mi: spacingMi,
  });
}

// 2nd half: send the checkpoint weather back; get risk levels and the recommendation.
export function scoreRoutes(loadLbs, routes) {
  return post('/api/score/', {
    load_lbs: loadLbs,
    routes: routes.map((r) => ({
      id: r.id,
      duration_s: r.duration_s,
      checkpoints: r.checkpoints.map((cp) => ({ mile: cp.mile, weather: cp.weather })),
    })),
  });
}

// Grid points around the routes for the weather heatmap.
export function heatmapPoints(paths) {
  return post('/api/heatmap/points/', { paths });
}

// Risk level for every heatmap point and hour, from the hourly weather.
export function scoreHeatmap(loadLbs, series) {
  return post('/api/heatmap/', { load_lbs: loadLbs, points: series });
}
