import { useState } from 'react';
import { Calendar, MapPin, Navigation, Weight } from 'lucide-react';

const pad = (n) => String(n).padStart(2, '0');

// Format a Date for <input type="datetime-local"> (local time, no zone).
const toLocalInput = (d) =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

// Default departure: the next full hour.
function nextHour() {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  d.setMinutes(0, 0, 0);
  return d;
}

const inputClass =
  'w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none';

const Field = ({ label, icon: Icon, children }) => (
  <div>
    <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
    <div className="relative">
      <Icon className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
      {children}
    </div>
  </div>
);

export default function TripForm({ onSubmit, loading }) {
  const [form, setForm] = useState(() => ({
    origin: '',
    destination: '',
    departureLocal: toLocalInput(nextHour()),
    loadLbs: 35000,
    spacingMi: 25,
  }));
  // The backend accepts departures from now up to 4 days ahead (forecast limit).
  const [limits] = useState(() => {
    const now = new Date();
    return {
      min: toLocalInput(now),
      max: toLocalInput(new Date(now.getTime() + 4 * 24 * 60 * 60 * 1000 - 60 * 60 * 1000)),
    };
  });

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ ...form, loadLbs: Number(form.loadLbs) });
  };

  return (
    <form onSubmit={handleSubmit} className="p-5 space-y-4 border-b border-slate-200">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Trip details</h2>

      <Field label="Origin" icon={MapPin}>
        <input required placeholder="e.g. Chicago, IL" value={form.origin} onChange={update('origin')} className={inputClass} />
      </Field>

      <Field label="Destination" icon={Navigation}>
        <input required placeholder="e.g. Denver, CO" value={form.destination} onChange={update('destination')} className={inputClass} />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Departure (your time)" icon={Calendar}>
          <input
            type="datetime-local"
            required
            min={limits.min}
            max={limits.max}
            value={form.departureLocal}
            onChange={update('departureLocal')}
            className={`${inputClass} pr-1 text-xs`}
          />
        </Field>
        <Field label="Load weight (lb)" icon={Weight}>
          <input
            type="number"
            required
            min={1}
            max={80000}
            value={form.loadLbs}
            onChange={update('loadLbs')}
            className={inputClass}
          />
        </Field>
      </div>

      <div>
        <span className="block text-xs font-medium text-slate-600 mb-1">Checkpoint spacing</span>
        <div className="flex gap-2">
          {[10, 25, 50].map((miles) => (
            <button
              key={miles}
              type="button"
              onClick={() => setForm((f) => ({ ...f, spacingMi: miles }))}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-colors ${
                form.spacingMi === miles
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
              }`}
            >
              {miles} miles
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
      >
        <Navigation className="w-4 h-4" />
        {loading ? 'Checking routes and weather…' : 'Find 3 routes'}
      </button>
    </form>
  );
}
