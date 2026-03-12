const API_BASE = import.meta.env.PROD ? '/api' : 'http://localhost:8000';
const HOME_ID = 1;

async function fetchJson(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getDashboard: () => fetchJson(`/homes/${HOME_ID}/dashboard`),

  getReadings: (params = {}) => {
    const sp = new URLSearchParams();
    if (params.from) sp.set('from', params.from);
    if (params.to) sp.set('to', params.to);
    if (params.device_id) sp.set('device_id', params.device_id);
    if (params.granularity) sp.set('granularity', params.granularity);
    return fetchJson(`/homes/${HOME_ID}/readings?${sp}`);
  },

  getAnomalies: (params = {}) => {
    const sp = new URLSearchParams();
    if (params.unacknowledged_only) sp.set('unacknowledged_only', 'true');
    if (params.severity) sp.set('severity', params.severity);
    if (params.device_id) sp.set('device_id', params.device_id);
    return fetchJson(`/homes/${HOME_ID}/anomalies?${sp}`);
  },

  acknowledgeAnomaly: (anomalyId) =>
    fetchJson(`/homes/${HOME_ID}/anomalies/${anomalyId}/acknowledge`, { method: 'POST' }),

  getForecast: () => fetchJson(`/homes/${HOME_ID}/forecast`),

  getDeviceBreakdown: () => fetchJson(`/homes/${HOME_ID}/devices/breakdown`),

  getComparison: () => fetchJson(`/homes/${HOME_ID}/compare`),

  whatIf: (deviceType, reductionPercent) =>
    fetchJson(`/homes/${HOME_ID}/what-if?device_type=${deviceType}&reduction_percent=${reductionPercent}`, {
      method: 'POST',
    }),

  uploadCsv: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/homes/${HOME_ID}/upload-csv`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },
};

export function createWebSocket(homeId = HOME_ID) {
  const wsBase = import.meta.env.PROD
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:8000';
  return new WebSocket(`${wsBase}/ws/homes/${homeId}/live`);
}
