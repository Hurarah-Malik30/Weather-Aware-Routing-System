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

export function planTrip({ origin, destination, departureLocal, loadLbs, spacingMi }) {
  return post('/api/plan/', {
    origin,
    destination,
    // datetime-local gives local time with no zone; convert to UTC at submit time.
    departure_utc: new Date(departureLocal).toISOString(),
    load_lbs: loadLbs,
    spacing_mi: spacingMi,
  });
}

// Weather grid around all 3 routes for hours 0-48 after departure.
export function fetchHeatmap(plan) {
  return post('/api/heatmap/', {
    departure_utc: plan.departure_utc,
    load_lbs: plan.load_lbs,
    // Checkpoints are a light outline of each route (one point every 10-50 miles).
    paths: plan.routes.map((r) => r.checkpoints.map((cp) => [cp.lon, cp.lat])),
  });
}
