import { useMemo, useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../utils/api';
import { formatCurrency, formatKwh, formatDate } from '../utils/format';
import { CardSkeleton, ChartSkeleton, ErrorState, EmptyState } from '../components/common/Skeleton';
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';
import { TrendingUp, Sliders, DollarSign, PieChart } from 'lucide-react';

function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const item = payload.find((p) => p.dataKey === 'actual' || p.dataKey === 'predicted');
  const point = item?.payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 shadow-xl">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      {point?.actual != null && (
        <p className="text-sm text-ww-blue-300">Actual: {formatKwh(point.actual)}</p>
      )}
      {point?.predicted != null && (
        <p className="text-sm text-ww-amber-300">Predicted: {formatKwh(point.predicted)}</p>
      )}
      {point?.predicted != null && (
        <p className="text-xs text-slate-500 mt-1">
          Band: {formatKwh(point.lower)} - {formatKwh(point.upper)}
        </p>
      )}
    </div>
  );
}

const LOOKBACK_DAYS = 60;

export default function Forecast() {
  const { data: forecast, loading, error, reload } = useFetch(() => api.getForecast(), []);
  const { data: readings, loading: readingsLoading } = useFetch(
    () =>
      api.getReadings({
        granularity: 'day',
        from: new Date(Date.now() - LOOKBACK_DAYS * 24 * 60 * 60 * 1000).toISOString(),
        to: new Date().toISOString(),
      }),
    []
  );
  const { data: devices } = useFetch(() => api.getDeviceBreakdown(), []);

  const [whatIfDevice, setWhatIfDevice] = useState('hvac');
  const [whatIfReduction, setWhatIfReduction] = useState(20);
  const [whatIfResult, setWhatIfResult] = useState(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);
  const [whatIfError, setWhatIfError] = useState(null);

  const handleWhatIf = async () => {
    setWhatIfLoading(true);
    setWhatIfError(null);
    try {
      const result = await api.whatIf(whatIfDevice, whatIfReduction);
      setWhatIfResult(result);
    } catch (e) {
      setWhatIfError(e.message || 'Could not calculate savings');
    } finally {
      setWhatIfLoading(false);
    }
  };

  const chartData = useMemo(() => {
    const actualPoints = (readings || []).map((r) => ({
      date: formatDate(r.period),
      actual: r.total_kwh,
      predicted: null,
      lower: null,
      upper: null,
      band: null,
      isForecast: false,
    }));

    const forecastPoints = (forecast?.daily_predictions || []).map((p) => ({
      date: formatDate(p.date),
      actual: null,
      predicted: p.predicted_kwh,
      lower: p.lower_bound,
      upper: p.upper_bound,
      band: Math.max((p.upper_bound || 0) - (p.lower_bound || 0), 0),
      isForecast: true,
    }));

    return [...actualPoints, ...forecastPoints];
  }, [readings, forecast?.daily_predictions]);

  const forecastStart = useMemo(() => {
    if (!forecast?.daily_predictions?.length) return null;
    return formatDate(forecast.daily_predictions[0].date);
  }, [forecast?.daily_predictions]);

  const predictedByCategory = useMemo(() => {
    if (!forecast || !devices?.length) return [];
    const grouped = devices.reduce((acc, d) => {
      if (!acc[d.device_type]) {
        acc[d.device_type] = {
          device_type: d.device_type,
          current_cost: 0,
          current_kwh: 0,
        };
      }
      acc[d.device_type].current_cost += d.monthly_cost;
      acc[d.device_type].current_kwh += d.monthly_kwh;
      return acc;
    }, {});

    const categories = Object.values(grouped);
    const totalCost = categories.reduce((sum, c) => sum + c.current_cost, 0);
    if (!totalCost) return [];

    return categories
      .map((c) => {
        const share = c.current_cost / totalCost;
        return {
          ...c,
          predicted_cost: forecast.predicted_cost * share,
          predicted_kwh: forecast.predicted_kwh * share,
          share_pct: share * 100,
          label: c.device_type.replaceAll('_', ' '),
        };
      })
      .sort((a, b) => b.predicted_cost - a.predicted_cost);
  }, [forecast, devices]);

  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div className="space-y-6 page-enter page-enter-active">
      <div>
        <h2 className="text-2xl font-bold text-white">Forecast</h2>
        <p className="text-sm text-slate-500 mt-1">Bill prediction and what-if analysis</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : forecast ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="kpi-card">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Predicted Bill</span>
              <DollarSign className="w-5 h-5 text-ww-amber-400" />
            </div>
            <p className="text-3xl font-bold text-white">{formatCurrency(forecast.predicted_cost)}</p>
            <p className="text-sm text-slate-500 mt-1">{forecast.forecast_month}</p>
          </div>
          <div className="kpi-card">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Predicted Usage</span>
              <TrendingUp className="w-5 h-5 text-ww-blue-400" />
            </div>
            <p className="text-3xl font-bold text-white">{formatKwh(forecast.predicted_kwh, 0)}</p>
            <p className="text-sm text-slate-500 mt-1">Next 30 days</p>
          </div>
          <div className="kpi-card">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs text-slate-500 uppercase tracking-wider">Confidence</span>
              <span className="text-lg text-ww-blue-300">{Math.round(forecast.confidence_score * 100)}%</span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Range: {formatCurrency(forecast.confidence_lower)} - {formatCurrency(forecast.confidence_upper)}
            </p>
            <div className="w-full bg-slate-800 rounded-full h-2 mt-3">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-ww-blue-500 to-ww-amber-500"
                style={{ width: `${forecast.confidence_score * 100}%` }}
              />
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={TrendingUp}
          title="No forecast available"
          description="We need at least 7 days of data to generate a forecast. Keep collecting data!"
        />
      )}

      {readingsLoading ? (
        <ChartSkeleton />
      ) : chartData.length > 0 ? (
        <div className="card">
          <h3 className="text-sm font-medium text-slate-400 mb-4">
            Last 60 Days Actual + Next 30 Days Predicted
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 6, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#64748b' }}
                axisLine={false}
                tickLine={false}
                width={50}
              />
              <Tooltip content={<ForecastTooltip />} />
              <Legend
                verticalAlign="top"
                height={34}
                formatter={(value) => <span className="text-xs text-slate-400">{value}</span>}
              />
              {forecastStart && (
                <ReferenceLine
                  x={forecastStart}
                  stroke="#64748b"
                  strokeDasharray="4 4"
                  label={{ value: 'Forecast start', fill: '#64748b', fontSize: 10, position: 'insideTopRight' }}
                />
              )}
              <Area
                type="monotone"
                dataKey="lower"
                stackId="confidence"
                stroke="none"
                fill="transparent"
                connectNulls={false}
                name=""
              />
              <Area
                type="monotone"
                dataKey="band"
                stackId="confidence"
                stroke="none"
                fill="#f59e0b22"
                connectNulls={false}
                name="Confidence Band"
              />
              <Line
                type="monotone"
                dataKey="actual"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                name="Actual"
              />
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#f59e0b"
                strokeWidth={2}
                strokeDasharray="6 3"
                dot={false}
                connectNulls={false}
                name="Predicted"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState
          icon={TrendingUp}
          title="No chart data"
          description="Seed data first to visualize historical and forecasted usage."
        />
      )}

      {predictedByCategory.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="w-5 h-5 text-ww-blue-400" />
            <h3 className="text-sm font-medium text-slate-400">Predicted Cost by Device Category</h3>
          </div>
          <div className="space-y-3">
            {predictedByCategory.map((item) => (
              <div key={item.device_type} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize text-slate-200">{item.label}</span>
                  <span className="text-ww-amber-300 font-semibold">{formatCurrency(item.predicted_cost)}</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-gradient-to-r from-ww-blue-500 to-ww-amber-500"
                    style={{ width: `${Math.min(item.share_pct, 100)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{formatKwh(item.predicted_kwh)}</span>
                  <span>{item.share_pct.toFixed(1)}% of forecast</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-5 h-5 text-ww-amber-400" />
          <h3 className="text-sm font-medium text-slate-400">What-If Analysis</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-500 mb-2">Device Category</label>
              <select
                value={whatIfDevice}
                onChange={(e) => setWhatIfDevice(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
              >
                <option value="hvac">HVAC / Air Conditioning</option>
                <option value="fridge">Refrigerator</option>
                <option value="ev_charger">EV Charger</option>
                <option value="washer_dryer">Washer / Dryer</option>
                <option value="lights">Lighting</option>
                <option value="vampire">Standby / Vampire Loads</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-500 mb-2">
                Reduce usage by: <span className="text-white font-bold">{whatIfReduction}%</span>
              </label>
              <input
                type="range"
                min="5"
                max="100"
                step="5"
                value={whatIfReduction}
                onChange={(e) => setWhatIfReduction(Number(e.target.value))}
                className="w-full accent-ww-blue-500"
              />
              <div className="flex justify-between text-xs text-slate-600 mt-1">
                <span>5%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            <button onClick={handleWhatIf} className="btn-primary w-full" disabled={whatIfLoading}>
              {whatIfLoading ? 'Calculating...' : 'Calculate Savings'}
            </button>
            {whatIfError && <p className="text-xs text-red-400">{whatIfError}</p>}
          </div>

          {whatIfResult && (
            <div className="bg-slate-800/50 rounded-xl p-5 space-y-3">
              <h4 className="text-sm font-medium text-white">Results</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-slate-500">Current Monthly</p>
                  <p className="text-lg font-bold text-white">{formatKwh(whatIfResult.current_monthly_kwh)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">New Monthly</p>
                  <p className="text-lg font-bold text-emerald-400">{formatKwh(whatIfResult.new_monthly_kwh)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Energy Saved</p>
                  <p className="text-lg font-bold text-ww-blue-400">{formatKwh(whatIfResult.saved_kwh)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Money Saved</p>
                  <p className="text-lg font-bold text-ww-amber-400">{formatCurrency(whatIfResult.saved_cost)}</p>
                </div>
              </div>
              <div className="mt-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <p className="text-xs text-emerald-400">
                  Reducing {whatIfResult.device_type.replaceAll('_', ' ')} usage by {whatIfResult.reduction_percent}%
                  saves {formatCurrency(whatIfResult.saved_cost)}/month
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
