import { useEffect, useRef, useState } from 'react';
import { Truck } from 'lucide-react';
import { pingServer } from './api';
import { fetchHeatmap, planTrip } from './lib/plan';
import { hourTime, truckPosition } from './lib/heatmap';
import TripForm from './components/TripForm';
import RouteCards from './components/RouteCards';
import RouteMap from './components/RouteMap';
import WeatherPanel from './components/WeatherPanel';

export default function App() {
  const [plan, setPlan] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [focus, setFocus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [heatmap, setHeatmap] = useState(null);
  const [heatLoading, setHeatLoading] = useState(false);
  const [heatError, setHeatError] = useState('');
  const [hour, setHour] = useState(0);
  const [metric, setMetric] = useState('risk');
  const requestId = useRef(0);
  const [server, setServer] = useState('checking'); // checking | waking | ready | down

  // Wake the backend as soon as the page opens. If it takes more than 2.5 s,
  // it's a cold start on Render's free plan, so tell the user why.
  useEffect(() => {
    let finished = false;
    const slow = setTimeout(() => {
      if (!finished) setServer('waking');
    }, 2500);
    pingServer()
      .then(() => setServer('ready'))
      .catch(() => setServer('down'))
      .finally(() => {
        finished = true;
        clearTimeout(slow);
      });
    return () => clearTimeout(slow);
  }, []);

  // The heatmap loads after the routes, so the routes appear without waiting for it.
  async function loadHeatmap(newPlan, id) {
    setHeatLoading(true);
    setHeatError('');
    try {
      const data = await fetchHeatmap(newPlan);
      if (id === requestId.current) setHeatmap(data);
    } catch (err) {
      if (id === requestId.current) setHeatError(err.message);
    } finally {
      if (id === requestId.current) setHeatLoading(false);
    }
  }

  async function handlePlan(form) {
    const id = ++requestId.current;   // ignore answers to older requests
    setLoading(true);
    setError('');
    try {
      const data = await planTrip(form);
      if (id !== requestId.current) return;
      setPlan(data);
      setSelectedId(data.recommended_route_id);
      setFocus(null);
      setHeatmap(null);
      setHour(0);
      loadHeatmap(data, id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const selectedRoute = plan?.routes.find((r) => r.id === selectedId);
  const truck = heatmap && selectedRoute ? truckPosition(selectedRoute, hourTime(heatmap, hour)) : null;

  return (
    <div className="h-full md:overflow-hidden flex flex-col md:flex-row bg-slate-50 text-slate-900">
      <aside className="md:w-[420px] md:h-full md:overflow-y-auto bg-white border-r border-slate-200 shrink-0">
        <header className="p-5 bg-slate-900 text-white flex items-center gap-3">
          <Truck className="w-7 h-7 text-blue-400" />
          <div>
            <h1 className="text-lg font-bold tracking-tight">Weather-Aware Routing System</h1>
            <p className="text-xs text-slate-400">Risk checked at the truck's ETA at every checkpoint</p>
          </div>
        </header>

        {server === 'waking' && (
          <div className="mx-5 mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900">
            Waking up the server (free hosting sleeps when idle). The first request can take up to a minute.
          </div>
        )}
        {server === 'down' && (
          <div className="mx-5 mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800">
            Can't reach the server right now. Please try again in a minute.
          </div>
        )}

        <TripForm onSubmit={handlePlan} loading={loading} />

        {error && (
          <div className="mx-5 mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-800">{error}</div>
        )}

        {plan ? (
          <RouteCards plan={plan} selectedId={selectedId} onSelect={setSelectedId} onFocusCheckpoint={setFocus} />
        ) : (
          !error && (
            <p className="p-8 text-center text-sm text-slate-400">
              Enter a trip to compare 3 routes by weather risk along the way.
            </p>
          )
        )}
      </aside>

      <main className="relative flex-1 min-h-[60vh]">
        <RouteMap
          plan={plan}
          selectedId={selectedId}
          onSelectRoute={setSelectedId}
          focus={focus}
          heatmap={heatmap}
          hour={hour}
          metric={metric}
          truck={truck}
        />
        {plan && (
          <WeatherPanel
            heatmap={heatmap}
            loading={heatLoading}
            error={heatError}
            hour={hour}
            onHourChange={setHour}
            metric={metric}
            onMetricChange={setMetric}
            truckStatus={truck?.status ?? '-'}
          />
        )}
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center text-sm font-medium text-slate-700">
            Fetching routes and forecasts…
          </div>
        )}
      </main>
    </div>
  );
}
