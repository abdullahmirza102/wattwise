import { useFetch } from '../hooks/useFetch';
import { api } from '../utils/api';
import { formatCurrency, formatKwh } from '../utils/format';
import { CardSkeleton, ErrorState, EmptyState } from '../components/common/Skeleton';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
} from 'recharts';
import {
  Thermometer, Snowflake, Car, WashingMachine, Lightbulb, Plug,
  Clock, ArrowDownRight, Cpu,
} from 'lucide-react';

const iconMap = {
  hvac: Thermometer,
  fridge: Snowflake,
  ev_charger: Car,
  washer_dryer: WashingMachine,
  lights: Lightbulb,
  vampire: Plug,
};

const COLORS = ['#3b82f6', '#f59e0b', '#8b5cf6', '#10b981', '#ec4899', '#6366f1'];

function DonutTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-sm font-medium text-white">{d.device_name}</p>
      <p className="text-xs text-slate-400">{formatKwh(d.monthly_kwh)} &middot; {formatCurrency(d.monthly_cost)}</p>
    </div>
  );
}

export default function Devices() {
  const { data, loading, error, reload } = useFetch(() => api.getDeviceBreakdown(), []);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!loading && (!data || data.length === 0)) {
    return <EmptyState icon={Cpu} title="No devices found" description="Add devices to your home to see the breakdown." />;
  }

  const pieData = data?.map((d) => ({
    ...d,
    name: d.device_name,
    value: d.monthly_kwh,
  })) || [];

  const totalCost = data?.reduce((sum, d) => sum + d.monthly_cost, 0) || 0;

  return (
    <div className="space-y-6 page-enter page-enter-active">
      <div>
        <h2 className="text-2xl font-bold text-white">Devices</h2>
        <p className="text-sm text-slate-500 mt-1">Appliance-level energy breakdown this month</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <CardSkeleton className="lg:col-span-1" />
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Donut Chart */}
          <div className="card lg:col-span-1 flex flex-col items-center">
            <h3 className="text-sm font-medium text-slate-400 mb-4 self-start">Cost Share</h3>
            <div className="relative">
              <ResponsiveContainer width={220} height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<DonutTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white">{formatCurrency(totalCost)}</span>
                <span className="text-xs text-slate-500">Total</span>
              </div>
            </div>
            {/* Legend */}
            <div className="mt-4 space-y-2 w-full">
              {data.map((d, i) => (
                <div key={d.device_id} className="flex items-center gap-2 text-xs">
                  <div className="w-3 h-3 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="text-slate-400 flex-1">{d.device_name}</span>
                  <span className="text-slate-300 font-medium">{d.percentage_of_total}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Device Cards */}
          <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {data.map((d, i) => {
              const Icon = iconMap[d.device_type] || Plug;
              const statusColor =
                d.status === 'anomalous' ? 'text-red-400' :
                d.status === 'active' ? 'text-emerald-400' : 'text-slate-600';
              const statusBg =
                d.status === 'anomalous' ? 'bg-red-500/10' :
                d.status === 'active' ? 'bg-emerald-500/10' : 'bg-slate-800';

              return (
                <div key={d.device_id} className="card-compact hover:border-slate-700 transition-all">
                  <div className="flex items-start gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-xl ${statusBg} flex items-center justify-center`}>
                      <Icon className={`w-5 h-5 ${statusColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-white truncate">{d.device_name}</h4>
                      <span className={`text-xs ${statusColor} capitalize`}>{d.status}</span>
                    </div>
                    <span className="text-lg font-bold text-white">{formatCurrency(d.monthly_cost)}</span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-500 mb-3">
                    <span>{formatKwh(d.monthly_kwh)}</span>
                    <span>{d.percentage_of_total}% of total</span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-slate-800 rounded-full h-1.5 mb-3">
                    <div
                      className="h-1.5 rounded-full transition-all duration-700"
                      style={{
                        width: `${Math.min(d.percentage_of_total, 100)}%`,
                        background: COLORS[i % COLORS.length],
                      }}
                    />
                  </div>

                  {/* Shift to save tip */}
                  {d.potential_savings > 0.5 && (
                    <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2 flex items-start gap-2">
                      <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-emerald-400">
                        Run after 11pm to save {formatCurrency(d.potential_savings)}/mo
                      </p>
                    </div>
                  )}

                  {d.cheapest_hour != null && d.potential_savings <= 0.5 && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-600">
                      <Clock className="w-3 h-3" />
                      <span>Cheapest at {d.cheapest_hour}:00</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
