import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ChevronRight, X } from 'lucide-react';
import { formatTimeAgo, severityColors } from '../../utils/format';

export default function AnomalyBanner({ anomalies, onDismiss }) {
  const navigate = useNavigate();

  if (!anomalies?.length) return null;

  const critical = anomalies.filter((a) => a.severity === 'critical');
  const warnings = anomalies.filter((a) => a.severity === 'warning');
  const display = critical.length > 0 ? critical[0] : warnings[0] || anomalies[0];

  const colors = severityColors[display.severity] || severityColors.info;
  const count = anomalies.filter((a) => !a.is_acknowledged).length;

  return (
    <div className={`${colors.bg} border ${colors.border} rounded-xl px-4 py-3 flex items-center gap-3`}>
      <AlertTriangle className={`w-5 h-5 ${colors.text} flex-shrink-0`} />
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${colors.text}`}>
          {count} active anomal{count === 1 ? 'y' : 'ies'} detected
        </p>
        <p className="text-xs text-slate-400 truncate mt-0.5">
          {display.description} &middot; {formatTimeAgo(display.detected_at)}
        </p>
      </div>
      <button
        onClick={() => navigate('/anomalies')}
        className={`flex items-center gap-1 text-xs font-medium ${colors.text} hover:underline flex-shrink-0`}
      >
        View All <ChevronRight className="w-3.5 h-3.5" />
      </button>
      {onDismiss && (
        <button onClick={onDismiss} className="text-slate-500 hover:text-slate-300 flex-shrink-0">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
