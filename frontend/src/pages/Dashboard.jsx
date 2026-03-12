import { useState } from 'react';
import { useFetch, useWebSocket } from '../hooks/useFetch';
import { api } from '../utils/api';
import KpiCards from '../components/dashboard/KpiCards';
import PowerGauge from '../components/dashboard/PowerGauge';
import ConsumptionChart from '../components/dashboard/ConsumptionChart';
import AnomalyBanner from '../components/dashboard/AnomalyBanner';
import { CardSkeleton, ChartSkeleton, ErrorState } from '../components/common/Skeleton';
import { formatCurrency, formatKwh } from '../utils/format';

export default function Dashboard() {
  const { data, loading, error, reload } = useFetch(() => api.getDashboard(), []);
  const { lastMessage, connected } = useWebSocket('/ws/homes/1/live');
  const [bannerDismissed, setBannerDismissed] = useState(false);

  if (error) return <ErrorState message={error} onRetry={reload} />;

  const liveWatts = lastMessage?.total_watts ?? data?.kpi?.current_wattage;
  const unackAnomalies = data?.recent_anomalies?.filter((a) => !a.is_acknowledged) ?? [];

  return (
    <div className="space-y-6 page-enter page-enter-active">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">Dashboard</h2>
        <p className="text-sm text-slate-500 mt-1">
          {data ? `${data.home_name} energy overview` : 'Loading...'}
        </p>
      </div>

      {/* Anomaly Banner */}
      {!bannerDismissed && unackAnomalies.length > 0 && (
        <AnomalyBanner anomalies={unackAnomalies} onDismiss={() => setBannerDismissed(true)} />
      )}

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        data?.kpi && <KpiCards kpi={data.kpi} />
      )}

      {/* Gauge + Chart row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <PowerGauge watts={liveWatts} connected={connected} />
        </div>
        <div className="lg:col-span-2">
          {loading ? <ChartSkeleton /> : <ConsumptionChart data={data?.daily_consumption} />}
        </div>
      </div>

      {/* Device breakdown quick view */}
      {data?.top_devices?.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-slate-400 mb-4">Top Consumers This Month</h3>
          <div className="space-y-3">
            {data.top_devices.slice(0, 5).map((d) => (
              <div key={d.device_id} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-200">{d.device_name}</span>
                    <span className="text-sm text-slate-400">{formatCurrency(d.monthly_cost)}</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-ww-blue-500 to-ww-blue-400 transition-all duration-700"
                      style={{ width: `${Math.min(d.percentage_of_total, 100)}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs text-slate-500 w-12 text-right">
                  {d.percentage_of_total}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Comparison */}
      {data?.comparison && (
        <div className="card">
          <h3 className="text-sm font-medium text-slate-400 mb-4">Month Comparison</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-slate-800/50 rounded-xl">
              <p className="text-xs text-slate-500 mb-1">This Month</p>
              <p className="text-xl font-bold text-white">{formatCurrency(data.comparison.this_month_cost)}</p>
              <p className="text-xs text-slate-500">{formatKwh(data.comparison.this_month_kwh)}</p>
            </div>
            <div className="text-center p-4 bg-slate-800/50 rounded-xl">
              <p className="text-xs text-slate-500 mb-1">Last Month</p>
              <p className="text-xl font-bold text-slate-300">
                {data.comparison.last_month_cost != null ? formatCurrency(data.comparison.last_month_cost) : '--'}
              </p>
              <p className="text-xs text-slate-500">
                {data.comparison.last_month_kwh != null ? formatKwh(data.comparison.last_month_kwh) : '--'}
              </p>
            </div>
            <div className="text-center p-4 bg-slate-800/50 rounded-xl">
              <p className="text-xs text-slate-500 mb-1">Same Month Last Year</p>
              <p className="text-xl font-bold text-slate-300">
                {data.comparison.same_month_last_year_cost != null
                  ? formatCurrency(data.comparison.same_month_last_year_cost)
                  : '--'}
              </p>
              <p className="text-xs text-slate-500">
                {data.comparison.same_month_last_year_kwh != null
                  ? formatKwh(data.comparison.same_month_last_year_kwh)
                  : '--'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
