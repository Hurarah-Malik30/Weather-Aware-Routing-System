import { useEffect, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { formatEta } from '../lib/risk';
import { hourTime } from '../lib/heatmap';

const PLAY_SPEED_MS = 600;

export default function WeatherPanel({ heatmap, loading, error, hour, onHourChange, metric, onMetricChange, truckStatus }) {
  const [playing, setPlaying] = useState(false);
  const maxHour = Math.max((heatmap?.hours ?? 1) - 1, 0);

  // Advance one hour at a time while playing; loop back to 0 at the end.
  useEffect(() => {
    if (!playing) return undefined;
    const id = setInterval(() => onHourChange((h) => (h >= maxHour ? 0 : h + 1)), PLAY_SPEED_MS);
    return () => clearInterval(id);
  }, [playing, maxHour, onHourChange]);

  if (loading || error || !heatmap) {
    return (
      <div className="absolute left-1/2 -translate-x-1/2 bottom-3 bg-white/95 rounded-lg shadow border border-slate-200 px-4 py-2 text-xs text-slate-600">
        {error ? <span className="text-red-700">Weather map unavailable: {error}</span> : 'Loading weather map…'}
      </div>
    );
  }

  return (
    <div className="absolute left-1/2 -translate-x-1/2 bottom-3 w-[min(560px,calc(100%-24px))] bg-white/95 rounded-xl shadow-lg border border-slate-200 p-3 space-y-2">
      <div className="flex items-center justify-between gap-3 text-xs">
        <div className="font-semibold text-slate-800">
          +{hour} h · {formatEta(new Date(hourTime(heatmap, hour)).toISOString())}
        </div>
        <div className="flex rounded-lg border border-slate-300 overflow-hidden">
          {[
            ['risk', 'Risk'],
            ['wind', 'Wind'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => onMetricChange(value)}
              className={`px-3 py-1 font-medium ${metric === value ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 hover:bg-slate-50'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? 'Pause' : 'Play'}
          className="w-8 h-8 shrink-0 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center"
        >
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>
        <input
          type="range"
          min={0}
          max={maxHour}
          step={1}
          value={hour}
          onChange={(e) => onHourChange(Number(e.target.value))}
          className="flex-1 accent-blue-600"
          aria-label="Hours after departure"
        />
        <span className="w-12 text-right text-xs text-slate-500">{maxHour} h</span>
      </div>

      <div className="text-[11px] text-slate-500">
        {metric === 'risk' ? 'Risk for your load (Low areas stay clear).' : 'Wind speed on the risk scale (25/35/45/55 mph).'}{' '}
        Truck on selected route: <b className="text-slate-700">{truckStatus}</b>
      </div>
    </div>
  );
}
