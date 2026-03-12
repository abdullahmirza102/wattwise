import { useMemo, useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../utils/api';
import { formatCurrency, formatTimeAgo, formatDateTime, severityColors } from '../utils/format';
import { CardSkeleton, ErrorState, EmptyState } from '../components/common/Skeleton';
import {
  AlertTriangle, CheckCircle, Filter, Shield, Zap, Clock, RotateCcw,
} from 'lucide-react';

export default function Anomalies() {
  const [filter, setFilter] = useState({
    severity: '',
    deviceId: '',
    ackState: 'all',
    dateFrom: '',
    dateTo: '',
  });
  const isUnackOnly = filter.ackState === 'unack';
  const { data, loading, error, reload } = useFetch(
    () => api.getAnomalies({
      severity: filter.severity || undefined,
      device_id: filter.deviceId || undefined,
      unacknowledged_only: isUnackOnly || undefined,
    }),
    [filter.severity, filter.deviceId, isUnackOnly]
  );
  const { data: deviceBreakdown } = useFetch(() => api.getDeviceBreakdown(), []);
  const [acknowledging, setAcknowledging] = useState(new Set());
  const [actionError, setActionError] = useState(null);

  const handleAck = async (anomalyId) => {
    setActionError(null);
    setAcknowledging((prev) => new Set([...prev, anomalyId]));
    try {
      await api.acknowledgeAnomaly(anomalyId);
      await reload();
    } catch (e) {
      setActionError(e.message || 'Failed to acknowledge anomaly');
    } finally {
      setAcknowledging((prev) => {
        const next = new Set(prev);
        next.delete(anomalyId);
        return next;
      });
    }
  };

  if (error) return <ErrorState message={error} onRetry={reload} />;

  const anomalies = useMemo(() => {
    const source = data?.anomalies || [];
    return source.filter((a) => {
      if (filter.ackState === 'ack' && !a.is_acknowledged) return false;
      if (filter.ackState === 'unack' && a.is_acknowledged) return false;
      if (filter.dateFrom) {
        const start = new Date(`${filter.dateFrom}T00:00:00`);
        const anomalyDate = new Date(a.detected_at || 0);
        if (anomalyDate < start) return false;
      }
      if (filter.dateTo) {
        const end = new Date(`${filter.dateTo}T23:59:59`);
        const anomalyDate = new Date(a.detected_at || 0);
        if (anomalyDate > end) return false;
      }
      return true;
    });
  }, [data?.anomalies, filter.ackState, filter.dateFrom, filter.dateTo]);

  const total = data?.total || 0;
  const unackCount = data?.unacknowledged_count || 0;
  const deviceNameById = useMemo(() => {
    const map = new Map();
    (deviceBreakdown || []).forEach((d) => map.set(d.device_id, d.device_name));
    return map;
  }, [deviceBreakdown]);

  const severityIcon = (sev) => {
    if (sev === 'critical') return <Zap className="w-4 h-4" />;
    if (sev === 'warning') return <AlertTriangle className="w-4 h-4" />;
    return <Shield className="w-4 h-4" />;
  };

  const resetFilters = () => {
    setFilter({
      severity: '',
      deviceId: '',
      ackState: 'all',
      dateFrom: '',
      dateTo: '',
    });
  };

  return (
    <div className="space-y-6 page-enter page-enter-active">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Anomalies</h2>
          <p className="text-sm text-slate-500 mt-1">
            {unackCount} unacknowledged of {total} total
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Filter className="w-3.5 h-3.5" />
          <span>Timeline filters</span>
        </div>
      </div>

      <div className="card-compact grid grid-cols-1 lg:grid-cols-5 gap-3">
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Severity</span>
          <select
            value={filter.severity}
            onChange={(e) => setFilter((f) => ({ ...f, severity: e.target.value }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
          >
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Device</span>
          <select
            value={filter.deviceId}
            onChange={(e) => setFilter((f) => ({ ...f, deviceId: e.target.value }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
          >
            <option value="">All devices</option>
            {(deviceBreakdown || []).map((d) => (
              <option key={d.device_id} value={d.device_id}>{d.device_name}</option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">Status</span>
          <select
            value={filter.ackState}
            onChange={(e) => setFilter((f) => ({ ...f, ackState: e.target.value }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
          >
            <option value="all">All</option>
            <option value="unack">Unacknowledged</option>
            <option value="ack">Acknowledged</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs text-slate-500">From date</span>
          <input
            type="date"
            value={filter.dateFrom}
            onChange={(e) => setFilter((f) => ({ ...f, dateFrom: e.target.value }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
          />
        </label>
        <div className="space-y-1">
          <label className="block text-xs text-slate-500">To date</label>
          <div className="flex gap-2">
            <input
              type="date"
              value={filter.dateTo}
              onChange={(e) => setFilter((f) => ({ ...f, dateTo: e.target.value }))}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
            />
            <button onClick={resetFilters} className="btn-ghost px-3" title="Reset filters">
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {actionError && (
        <div className="card-compact border border-red-500/30 bg-red-500/10 text-xs text-red-300">
          {actionError}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : anomalies.length === 0 ? (
        <EmptyState
          icon={Shield}
          title="No anomalies found"
          description="Your energy usage looks normal. We'll alert you when something unusual is detected."
        />
      ) : (
        <div className="relative space-y-3 before:absolute before:left-[19px] before:top-2 before:bottom-2 before:w-px before:bg-slate-800">
          {anomalies.map((a) => {
            const colors = severityColors[a.severity] || severityColors.info;
            const isAcking = acknowledging.has(a.id);
            const deviceName = a.device_name || deviceNameById.get(a.device_id) || 'Unknown device';

            return (
              <div
                key={a.id}
                className={`card-compact border ml-6 relative ${a.is_acknowledged ? 'border-slate-800 opacity-60' : colors.border} transition-all`}
              >
                <span className={`absolute -left-7 top-4 h-3 w-3 rounded-full border-2 border-slate-950 ${colors.bg}`} />
                <div className="flex items-start gap-4">
                  {/* Severity indicator */}
                  <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                    <span className={colors.text}>{severityIcon(a.severity)}</span>
                  </div>

                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`badge ${colors.bg} ${colors.text} border ${colors.border} text-xs capitalize`}>
                          {a.severity}
                        </span>
                        <span className="badge bg-slate-800 text-slate-400 border-slate-700 text-xs">
                          {a.anomaly_type.replaceAll('_', ' ')}
                        </span>
                        <span className="text-xs text-slate-500">{deviceName}</span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-slate-600 flex-shrink-0">
                        <Clock className="w-3 h-3" />
                        {formatTimeAgo(a.detected_at)}
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-sm text-slate-300 mb-2">{a.description}</p>

                    {/* Footer */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        {a.estimated_extra_cost > 0 && (
                          <span>Est. extra cost: <span className="text-amber-400 font-medium">{formatCurrency(a.estimated_extra_cost)}</span></span>
                        )}
                        <span>{formatDateTime(a.detected_at)}</span>
                      </div>

                      {!a.is_acknowledged ? (
                        <button
                          onClick={() => handleAck(a.id)}
                          disabled={isAcking}
                          className="btn-ghost text-xs flex items-center gap-1.5"
                        >
                          <CheckCircle className="w-3.5 h-3.5" />
                          {isAcking ? 'Acknowledging...' : 'Acknowledge'}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-600 flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" /> Acknowledged
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
