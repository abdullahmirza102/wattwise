import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { formatCurrency, formatKwh } from '../../utils/format';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-sm font-semibold text-white">{formatKwh(d.kwh)}</p>
      <p className="text-xs text-slate-400">{formatCurrency(d.cost)}</p>
      {d.is_peak_heavy && (
        <p className="text-xs text-amber-400 mt-1">High peak usage</p>
      )}
    </div>
  );
}

export default function ConsumptionChart({ data }) {
  if (!data?.length) {
    return (
      <div className="card">
        <h3 className="text-sm font-medium text-slate-400 mb-4">7-Day Consumption</h3>
        <div className="flex items-center justify-center h-48 text-slate-600 text-sm">
          No consumption data yet
        </div>
      </div>
    );
  }

  const formattedData = data.map((d) => ({
    ...d,
    date: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
    shortDate: new Date(d.date).toLocaleDateString('en-US', { weekday: 'short' }),
  }));

  const avgKwh = data.reduce((sum, d) => sum + d.kwh, 0) / data.length;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-400">7-Day Consumption</h3>
        <span className="text-xs text-slate-600">
          Avg: {formatKwh(avgKwh)}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={formattedData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="colorKwh" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorPeak" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="shortDate"
            tick={{ fontSize: 11, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}`}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={avgKwh}
            stroke="#475569"
            strokeDasharray="3 3"
            label={false}
          />
          <Area
            type="monotone"
            dataKey="kwh"
            stroke="#3b82f6"
            fill="url(#colorKwh)"
            strokeWidth={2}
            dot={(props) => {
              const { cx, cy, payload } = props;
              return (
                <circle
                  key={cx}
                  cx={cx}
                  cy={cy}
                  r={4}
                  fill={payload.is_peak_heavy ? '#f59e0b' : '#3b82f6'}
                  stroke={payload.is_peak_heavy ? '#f59e0b' : '#3b82f6'}
                  strokeWidth={2}
                />
              );
            }}
            activeDot={{ r: 6, strokeWidth: 2, stroke: '#0f172a' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
