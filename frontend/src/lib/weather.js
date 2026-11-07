// Hourly forecasts from Open-Meteo, fetched by the browser.
//
// Open-Meteo's free tier counts every location as one call and limits each IP
// address (600/minute, 5,000/hour, 10,000/day). Fetching from the browser means
// every user spends their own quota, not the server's shared one. We also avoid
// asking for the same place twice: points are rounded to a ~3 mile grid and
// forecasts are kept for 30 minutes.

const OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast';
const BATCH_SIZE = 100;          // locations per request (keeps URLs a safe length)
const FORECAST_DAYS = 7;         // departure up to 4 days ahead + a long trip + 48 h heatmap
const SNAP_DEG = 0.05;           // ~3 miles, finer than the forecast model's own grid
const CACHE_TTL_MS = 30 * 60 * 1000;

const cache = new Map();         // "lat,lon" -> { fetchedAt, forecast }

const snap = (v) => (Math.round(v / SNAP_DEG) * SNAP_DEG).toFixed(2);
const keyOf = (p) => `${snap(p.lat)},${snap(p.lon)}`;

async function fetchBatch(keys) {
  const params = new URLSearchParams({
    latitude: keys.map((k) => k.split(',')[0]).join(','),
    longitude: keys.map((k) => k.split(',')[1]).join(','),
    hourly: 'wind_speed_10m,wind_gusts_10m,rain,snowfall',
    wind_speed_unit: 'mph',
    precipitation_unit: 'inch', // rain AND snowfall in inches
    timezone: 'UTC',
    forecast_days: String(FORECAST_DAYS),
  });

  let response;
  try {
    response = await fetch(`${OPEN_METEO_URL}?${params}`);
  } catch {
    throw new Error('Weather service unavailable: could not connect to Open-Meteo.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const reason = data?.reason || `HTTP ${response.status}`;
    throw new Error(`Weather service unavailable: ${reason}`);
  }

  // One location -> a single object; several -> a list.
  const locations = Array.isArray(data) ? data : [data];
  // Every location shares the same hours, so parse the times once.
  const times = locations[0].hourly.time.map((t) => Date.parse(`${t}Z`));
  return locations.map((loc) => ({
    times,
    wind: loc.hourly.wind_speed_10m.map((v) => v ?? 0),
    gust: loc.hourly.wind_gusts_10m.map((v) => v ?? 0),
    rain: loc.hourly.rain.map((v) => v ?? 0),
    snow: loc.hourly.snowfall.map((v) => v ?? 0),
  }));
}

// One forecast per point, in the same order as `points` ([{lat, lon}]).
export async function fetchForecasts(points) {
  const now = Date.now();
  for (const [key, entry] of cache) {
    if (now - entry.fetchedAt > CACHE_TTL_MS) cache.delete(key);
  }

  const keys = points.map(keyOf);
  const missing = [...new Set(keys.filter((k) => !cache.has(k)))];
  const batches = [];
  for (let i = 0; i < missing.length; i += BATCH_SIZE) batches.push(missing.slice(i, i + BATCH_SIZE));

  const results = await Promise.all(batches.map(fetchBatch));
  batches.forEach((batch, b) => batch.forEach((key, i) => cache.set(key, { fetchedAt: now, forecast: results[b][i] })));

  return keys.map((k) => cache.get(k).forecast);
}

const HOUR_MS = 3600 * 1000;

// Index of the forecast hour nearest to `ms`, or -1 if it's outside the forecast.
export function hourIndex(forecast, ms) {
  const i = Math.round((ms - forecast.times[0]) / HOUR_MS);
  return i >= 0 && i < forecast.times.length ? i : -1;
}

// Weather at the forecast hour nearest to `ms` (a UTC timestamp).
export function weatherAt(forecast, ms) {
  const i = hourIndex(forecast, ms);
  if (i < 0) throw new Error(`No forecast available for ${new Date(ms).toISOString()}`);
  return {
    time: new Date(forecast.times[i]).toISOString(),
    wind: forecast.wind[i],
    gust: forecast.gust[i],
    rain: forecast.rain[i],
    snow: forecast.snow[i],
  };
}
