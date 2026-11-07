// Risk levels match routing/risk.py: 0 Low ... 4 No Travel.
export const LEVELS = [
  { name: 'Low', color: '#16a34a', badge: 'bg-green-100 text-green-800 border-green-300' },
  { name: 'Moderate', color: '#eab308', badge: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  { name: 'High', color: '#f97316', badge: 'bg-orange-100 text-orange-800 border-orange-300' },
  { name: 'Severe', color: '#dc2626', badge: 'bg-red-100 text-red-800 border-red-300' },
  { name: 'No Travel', color: '#7e22ce', badge: 'bg-purple-100 text-purple-800 border-purple-300' },
];

export const levelInfo = (level) => LEVELS[level] ?? LEVELS[0];

export const maxLevel = (route) => Math.max(0, ...route.checkpoints.map((cp) => cp.level));

export function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h} h ${String(m).padStart(2, '0')} m`;
}

// ETAs come from the API in UTC; show them in the viewer's local time.
export function formatEta(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// OSRM geometry is a GeoJSON LineString; accept a bare [[lon, lat], ...] list too.
export const toLineString = (geometry) =>
  Array.isArray(geometry) ? { type: 'LineString', coordinates: geometry } : geometry;
