import { useMemo } from 'react';
import { formatCurrency, formatKwh, formatWatts, formatPercent } from '../../utils/format';
import {
  Zap, DollarSign, AlertTriangle, TrendingUp, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';

export default function KpiCards({ kpi }) {
  const cards = useMemo(() => [
    {
      label: "Today's Usage",
      value: formatKwh(kpi.today_kwh),
      sub: formatCurrency(kpi.today_cost),
      icon: Zap,
      color: 'text-ww-blue-400',
      glow: 'shadow-[0_0_15px_rgba(59,130,246,0.15)]',
    },
    {
      label: 'This Month',
      value: formatCurrency(kpi.month_cost),
      sub: formatKwh(kpi.month_kwh),
      icon: DollarSign,
      color: 'text-emerald-400',
      glow: 'shadow-[0_0_15px_rgba(52,211,153,0.15)]',
      badge: kpi.month_vs_last_month_pct != null
        ? { value: formatPercent(kpi.month_vs_last_month_pct), up: kpi.month_vs_last_month_pct > 0 }
        : null,
    },
    {
      label: 'Active Anomalies',
      value: kpi.active_anomalies,
      sub: kpi.active_anomalies > 0 ? 'Needs attention' : 'All clear',
      icon: AlertTriangle,
      color: kpi.active_anomalies > 0 ? 'text-amber-400' : 'text-slate-500',
      glow: kpi.active_anomalies > 0 ? 'shadow-[0_0_15px_rgba(245,158,11,0.15)]' : '',
    },
    {
      label: 'Predicted Bill',
      value: kpi.predicted_bill != null ? formatCurrency(kpi.predicted_bill) : '--',
      sub: 'Next 30 days',
      icon: TrendingUp,
      color: 'text-violet-400',
      glow: 'shadow-[0_0_15px_rgba(139,92,246,0.15)]',
    },
  ], [kpi]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.label} className={`kpi-card ${card.glow}`}>
          <div className="flex items-start justify-between mb-3">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
              {card.label}
            </span>
            <card.icon className={`w-5 h-5 ${card.color}`} />
          </div>
          <div className="flex items-end gap-2">
            <span className="text-2xl font-bold text-white">{card.value}</span>
            {card.badge && (
              <span className={`flex items-center gap-0.5 text-xs font-medium mb-1 ${
                card.badge.up ? 'text-red-400' : 'text-emerald-400'
              }`}>
                {card.badge.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {card.badge.value}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">{card.sub}</p>
        </div>
      ))}
    </div>
  );
}
