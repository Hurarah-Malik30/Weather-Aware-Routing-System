// Turn the /api/heatmap/ response into map data for one hour of the slider.

// Wind speed -> 0..1 on the same scale as risk levels (25/35/45/55 mph thresholds).
function windWeight(mph) {
  const stops = [0, 25, 35, 45, 55];
  if (mph >= 55) return 1;
  const i = stops.findIndex((s, k) => mph >= s && mph < stops[k + 1]);
  return (i + (mph - stops[i]) / (stops[i + 1] - stops[i])) / 4;
}

export function heatmapGeoJSON(heatmap, hour, metric) {
  return {
    type: 'FeatureCollection',
    features: (heatmap?.points ?? []).map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      properties: {
        w: metric === 'wind' ? windWeight(p.wind[hour]) : p.level[hour] / 4,
      },
    })),
  };
}

export const hourTime = (heatmap, hour) => new Date(heatmap.start_utc).getTime() + hour * 3600 * 1000;

// Where the truck is on `route` at time `ms`, interpolated between checkpoints.
export function truckPosition(route, ms) {
  const cps = route.checkpoints;
  const times = cps.map((cp) => new Date(cp.eta).getTime());
  if (ms < times[0]) return { lon: cps[0].lon, lat: cps[0].lat, status: 'Not departed' };
  if (ms >= times.at(-1)) return { lon: cps.at(-1).lon, lat: cps.at(-1).lat, status: 'Arrived' };

  const i = times.findIndex((t, k) => ms >= t && ms < times[k + 1]);
  const f = (ms - times[i]) / (times[i + 1] - times[i]);
  return {
    lon: cps[i].lon + f * (cps[i + 1].lon - cps[i].lon),
    lat: cps[i].lat + f * (cps[i + 1].lat - cps[i].lat),
    status: `Mile ${Math.round(cps[i].mile + f * (cps[i + 1].mile - cps[i].mile))}`,
  };
}
