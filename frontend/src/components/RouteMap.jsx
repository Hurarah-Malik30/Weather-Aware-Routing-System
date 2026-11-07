import { useEffect, useRef, useState } from 'react';
import { LngLatBounds, Map as MapLibreMap, Marker, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { LEVELS, formatEta, levelInfo, toLineString } from '../lib/risk';
import { heatmapGeoJSON } from '../lib/heatmap';

// Vite bundles MapLibre, so tell it where its web worker file ended up.
setWorkerUrl(workerUrl);

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron';
const EMPTY = { type: 'FeatureCollection', features: [] };

// Paint expression: risk level number -> colour.
const LEVEL_COLOR = ['match', ['get', 'level'], ...LEVELS.flatMap((l, i) => [i, l.color]), '#94a3b8'];

const escapeHtml = (text) =>
  String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

function popupHtml(p) {
  const info = levelInfo(p.level);
  return `
    <div style="font: 12px/1.45 system-ui, sans-serif; min-width: 190px">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:4px">
        <b>Route ${escapeHtml(p.routeId)} · Mile ${Math.round(p.mile)}</b>
        <span style="background:${info.color}; color:#fff; border-radius:999px; padding:1px 8px; font-weight:600">${info.name}</span>
      </div>
      <div>ETA: <b>${escapeHtml(formatEta(p.eta))}</b></div>
      <div>Wind: <b>${Math.round(p.wind)} mph</b> (gusts ${Math.round(p.gust)} mph)</div>
      <div>Rain: <b>${Number(p.rain).toFixed(2)} in/hr</b> · Snow: <b>${Number(p.snow).toFixed(2)} in/hr</b></div>
      <div style="margin-top:4px; color:#475569">${escapeHtml(p.reason)}</div>
    </div>`;
}

// Heatmap colours follow the same ramp as the risk levels; 0 stays transparent.
const HEAT_COLOR = [
  'interpolate', ['linear'], ['heatmap-density'],
  0, 'rgba(0, 0, 0, 0)',
  0.15, 'rgba(234, 179, 8, 0.45)',
  0.4, 'rgba(249, 115, 22, 0.65)',
  0.65, 'rgba(220, 38, 38, 0.75)',
  0.9, 'rgba(126, 34, 206, 0.85)',
];

// Flatten a checkpoint into map feature properties (MapLibre can't keep nested objects).
const checkpointFeature = (cp, routeId) => ({
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [cp.lon, cp.lat] },
  properties: {
    routeId,
    mile: cp.mile,
    eta: cp.eta,
    level: cp.level,
    reason: cp.reason,
    wind: cp.weather.wind,
    gust: cp.weather.gust,
    rain: cp.weather.rain,
    snow: cp.weather.snow,
  },
});

export default function RouteMap({ plan, selectedId, onSelectRoute, focus, heatmap, hour, metric, truck }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const onSelectRef = useRef(onSelectRoute);
  const [ready, setReady] = useState(false);

  // Keep the latest callback for map event handlers that are registered once.
  useEffect(() => {
    onSelectRef.current = onSelectRoute;
  });

  // 1. Create the map once, with empty sources we later fill via setData().
  useEffect(() => {
    const map = new MapLibreMap({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [-98.5, 39.8],
      zoom: 3.4,
    });
    mapRef.current = map;
    popupRef.current = new Popup({ closeButton: true, maxWidth: '280px' });
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');

    // MapLibre only notices window resizes; also follow the container's own size
    // (layout changes, DevTools opening), so the map never stays half-drawn.
    const container = containerRef.current;
    const observer = new ResizeObserver(() => {
      if (container.clientWidth > 0 && container.clientHeight > 0) map.resize();
    });
    observer.observe(container);

    const showPopup = (lngLat, props) => popupRef.current.setLngLat(lngLat).setHTML(popupHtml(props)).addTo(map);

    map.on('load', () => {
      map.addSource('routes', { type: 'geojson', data: EMPTY });
      map.addSource('checkpoints', { type: 'geojson', data: EMPTY });
      map.addSource('weather', { type: 'geojson', data: EMPTY });
      map.addSource('truck', { type: 'geojson', data: EMPTY });

      // Weather heatmap goes first so it sits underneath the routes.
      map.addLayer({
        id: 'weather-heat',
        type: 'heatmap',
        source: 'weather',
        paint: {
          'heatmap-weight': ['get', 'w'],
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 3, 0.9, 8, 1.4],
          'heatmap-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 12, 6, 45, 9, 300],
          'heatmap-color': HEAT_COLOR,
          'heatmap-opacity': 0.75,
        },
      });

      // White casing under each line so routes stand out from the base map.
      map.addLayer({
        id: 'routes-casing',
        type: 'line',
        source: 'routes',
        layout: { 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] },
        paint: { 'line-color': '#ffffff', 'line-width': ['case', ['get', 'selected'], 9, 6] },
      });
      map.addLayer({
        id: 'routes-line',
        type: 'line',
        source: 'routes',
        layout: { 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] },
        paint: {
          'line-color': ['case', ['get', 'selected'], '#2563eb', '#94a3b8'],
          'line-width': ['case', ['get', 'selected'], 5, 3],
        },
      });
      map.addLayer({
        id: 'checkpoints',
        type: 'circle',
        source: 'checkpoints',
        paint: {
          'circle-color': LEVEL_COLOR,
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, 3.5, 8, 7],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1.5,
        },
      });

      // Where the truck is at the slider's hour.
      map.addLayer({
        id: 'truck',
        type: 'circle',
        source: 'truck',
        paint: {
          'circle-color': '#0f172a',
          'circle-radius': 7,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 3,
        },
      });

      map.on('click', 'checkpoints', (e) => {
        const f = e.features[0];
        showPopup(f.geometry.coordinates, f.properties);
      });
      map.on('click', 'routes-line', (e) => {
        if (map.queryRenderedFeatures(e.point, { layers: ['checkpoints'] }).length) return;
        onSelectRef.current(e.features[0].properties.id);
      });
      for (const layer of ['checkpoints', 'routes-line']) {
        map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'));
        map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''));
      }

      setReady(true);
    });

    return () => {
      observer.disconnect();
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  // 2. Draw routes and the selected route's checkpoints whenever the data or selection changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const routes = plan?.routes ?? [];

    map.getSource('routes').setData({
      type: 'FeatureCollection',
      features: routes.map((r) => ({
        type: 'Feature',
        geometry: toLineString(r.geometry),
        properties: { id: r.id, selected: r.id === selectedId },
      })),
    });

    const selected = routes.find((r) => r.id === selectedId);
    map.getSource('checkpoints').setData({
      type: 'FeatureCollection',
      features: selected ? selected.checkpoints.map((cp) => checkpointFeature(cp, selected.id)) : [],
    });
  }, [ready, plan, selectedId]);

  // 3. On a new plan: fit the map to all routes and mark origin and destination.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !plan) return undefined;
    popupRef.current.remove();

    const bounds = new LngLatBounds();
    plan.routes.forEach((r) => toLineString(r.geometry).coordinates.forEach((c) => bounds.extend(c)));
    if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, duration: 800 });

    const markers = [
      new Marker({ color: '#0f172a' }).setLngLat([plan.origin.lon, plan.origin.lat]),
      new Marker({ color: '#2563eb' }).setLngLat([plan.destination.lon, plan.destination.lat]),
    ];
    markers.forEach((m) => m.addTo(map));
    return () => markers.forEach((m) => m.remove());
  }, [ready, plan]);

  // 4. Heatmap and truck for the slider's hour: only setData, the layers never change.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.getSource('weather').setData(heatmap ? heatmapGeoJSON(heatmap, hour, metric) : EMPTY);
  }, [ready, heatmap, hour, metric]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.getSource('truck').setData(
      truck
        ? { type: 'FeatureCollection', features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [truck.lon, truck.lat] }, properties: {} }] }
        : EMPTY,
    );
  }, [ready, truck]);

  // 5. A checkpoint clicked in the sidebar: fly there and open its popup.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !focus) return;
    map.flyTo({ center: [focus.lon, focus.lat], zoom: Math.max(map.getZoom(), 7) });
    const props = checkpointFeature(focus, focus.routeId).properties;
    popupRef.current.setLngLat([focus.lon, focus.lat]).setHTML(popupHtml(props)).addTo(map);
  }, [ready, focus]);

  return (
    <div className="absolute inset-0">
      {/* Inline style: maplibre-gl.css sets position: relative on the map, which would override a Tailwind class. */}
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />

      {/* Legend */}
      <div className="absolute left-3 top-3 bg-white/95 rounded-lg shadow border border-slate-200 px-3 py-2 text-xs space-y-1">
        <div className="font-semibold text-slate-700">Checkpoint risk</div>
        {LEVELS.map((l) => (
          <div key={l.name} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
            {l.name}
          </div>
        ))}
      </div>
    </div>
  );
}
