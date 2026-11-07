import { AlertTriangle, CheckCircle } from 'lucide-react';
import { LEVELS, formatDuration, formatEta, levelInfo, maxLevel } from '../lib/risk';

// Horizontal bar showing how many miles fall in each risk level.
function RiskBar({ milesByLevel }) {
  const total = LEVELS.reduce((sum, l) => sum + (milesByLevel[l.name] || 0), 0);
  if (!total) return null;
  return (
    <div className="flex h-2 w-full rounded-full overflow-hidden bg-slate-100">
      {LEVELS.map((l) => {
        const miles = milesByLevel[l.name] || 0;
        return miles > 0 ? (
          <div key={l.name} style={{ width: `${(miles / total) * 100}%`, background: l.color }} title={`${l.name}: ${miles} mi`} />
        ) : null;
      })}
    </div>
  );
}

const Badge = ({ level }) => (
  <span className={`px-2 py-0.5 text-[11px] font-semibold rounded-full border ${levelInfo(level).badge}`}>
    {levelInfo(level).name}
  </span>
);

function CheckpointList({ route, onFocus }) {
  return (
    <details className="border-t border-slate-100">
      <summary className="px-4 py-2 text-xs font-medium text-blue-700 cursor-pointer select-none">
        {route.checkpoints.length} checkpoints
      </summary>
      <ul className="max-h-64 overflow-y-auto divide-y divide-slate-100">
        {route.checkpoints.map((cp) => (
          <li key={cp.mile}>
            <button
              type="button"
              onClick={() => onFocus({ ...cp, routeId: route.id })}
              className="w-full px-4 py-2 flex items-center gap-3 text-left text-xs hover:bg-slate-50"
            >
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: levelInfo(cp.level).color }} />
              <span className="w-14 font-semibold text-slate-800">Mi {Math.round(cp.mile)}</span>
              <span className="flex-1 text-slate-600">{formatEta(cp.eta)}</span>
              <span className="text-slate-500">{Math.round(cp.weather.wind)} mph</span>
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}

export default function RouteCards({ plan, selectedId, onSelect, onFocusCheckpoint }) {
  const anySafe = plan.routes.some((r) => !r.summary.has_no_travel);

  return (
    <div className="p-5 space-y-3">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Routes</h2>

      <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-sm text-emerald-900">
        <span className="font-semibold">Recommended: Route {plan.recommended_route_id}.</span> {plan.recommendation_reason}
      </div>

      {!anySafe && (
        <div className="p-3 rounded-lg bg-purple-50 border border-purple-200 text-sm text-purple-900 flex gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          Every route crosses No Travel conditions at this departure time. Try a later departure.
        </div>
      )}

      {plan.routes.map((route) => {
        const selected = route.id === selectedId;
        const recommended = route.id === plan.recommended_route_id;
        const s = route.summary;
        return (
          <div
            key={route.id}
            className={`rounded-xl border bg-white transition-shadow ${
              selected ? 'border-blue-600 ring-2 ring-blue-500/20 shadow-md' : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <button type="button" onClick={() => onSelect(route.id)} className="w-full p-4 text-left space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-slate-800 text-sm">
                  Route {route.id}
                  {route.is_detour && <span className="ml-2 text-[11px] font-medium text-slate-500">(via detour)</span>}
                </span>
                {recommended && (
                  <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[11px] font-bold rounded-full border border-emerald-300 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Recommended
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600">
                <div>Distance: <b className="text-slate-800">{route.distance_mi} mi</b></div>
                <div>Drive time: <b className="text-slate-800">{formatDuration(route.duration_s)}</b></div>
                <div className="col-span-2">Arrives: <b className="text-slate-800">{formatEta(route.arrival_utc)}</b></div>
                <div>Severe: <b className="text-red-600">{s.severe_miles} mi</b></div>
                <div>High: <b className="text-orange-600">{s.high_miles} mi</b></div>
                <div>No Travel: <b className="text-purple-700">{s.no_travel_miles} mi</b></div>
                <div>Avg risk: <b className="text-slate-800">{s.avg_risk} / 4</b></div>
              </div>

              <RiskBar milesByLevel={s.miles_by_level} />

              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Worst checkpoint</span>
                <Badge level={maxLevel(route)} />
              </div>
            </button>

            {selected && <CheckpointList route={route} onFocus={onFocusCheckpoint} />}
          </div>
        );
      })}
    </div>
  );
}
