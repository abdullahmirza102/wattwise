import { useState, useCallback, useMemo } from 'react';
import { api } from '../utils/api';
import { Upload as UploadIcon, FileText, CheckCircle, AlertCircle, X } from 'lucide-react';

function parseCsvLine(line) {
  const values = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"') {
      current += '"';
      i += 1;
      continue;
    }
    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (char === ',' && !inQuotes) {
      values.push(current.trim());
      current = '';
      continue;
    }
    current += char;
  }
  values.push(current.trim());
  return values;
}

function detectDefaultMapping(headers) {
  const normalized = headers.map((h) => h.trim().toLowerCase());
  const timestampKeys = ['timestamp', 'datetime', 'date_time', 'time', 'date'];
  const kwhKeys = ['kwh', 'kwh_consumed', 'consumption', 'usage', 'energy'];

  const tsIdx = normalized.findIndex((h) => timestampKeys.some((key) => h.includes(key)));
  const kwhIdx = normalized.findIndex((h) => kwhKeys.some((key) => h.includes(key)));

  return {
    timestamp: tsIdx >= 0 ? headers[tsIdx] : '',
    kwh: kwhIdx >= 0 ? headers[kwhIdx] : '',
  };
}

export default function Upload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({ timestamp: '', kwh: '' });
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [parseError, setParseError] = useState(null);

  const parsePreview = useCallback((f) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target.result;
        const lines = text
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);

        if (lines.length < 2) {
          setParseError('CSV must include a header row and at least one data row.');
          setPreview(null);
          return;
        }

        const headers = parseCsvLine(lines[0]);
        const rows = lines.slice(1).map((line) => parseCsvLine(line));
        const defaults = detectDefaultMapping(headers);

        setMapping(defaults);
        setPreview({
          headers,
          rows: rows.slice(0, 10),
          allRows: rows,
          totalRows: rows.length,
        });
        setParseError(null);
      } catch (err) {
        setParseError('Unable to parse CSV. Please check file format.');
        setPreview(null);
      }
    };
    reader.readAsText(f);
  }, []);

  const handleFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) {
      setParseError('Please select a .csv file');
      return;
    }
    setFile(f);
    setResult(null);
    setParseError(null);
    parsePreview(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    handleFile(f);
  };

  const mappedPreviewRows = useMemo(() => {
    if (!preview || !mapping.timestamp || !mapping.kwh) return [];
    const tsIdx = preview.headers.indexOf(mapping.timestamp);
    const kwhIdx = preview.headers.indexOf(mapping.kwh);
    if (tsIdx < 0 || kwhIdx < 0) return [];
    return preview.rows.map((row) => ({
      timestamp: row[tsIdx] || '',
      kwh: row[kwhIdx] || '',
    }));
  }, [preview, mapping]);

  const handleUpload = async () => {
    if (!file || !preview) return;
    if (!mapping.timestamp || !mapping.kwh) {
      setResult({ status: 'error', message: 'Map both timestamp and kWh columns before importing.' });
      return;
    }

    const tsIdx = preview.headers.indexOf(mapping.timestamp);
    const kwhIdx = preview.headers.indexOf(mapping.kwh);
    if (tsIdx < 0 || kwhIdx < 0) {
      setResult({ status: 'error', message: 'Selected column mapping is invalid.' });
      return;
    }

    const normalizedRows = preview.allRows
      .map((row) => [row[tsIdx]?.trim(), row[kwhIdx]?.trim()])
      .filter(([timestamp, kwh]) => timestamp && kwh);
    const csv = ['timestamp,kwh', ...normalizedRows.map(([timestamp, kwh]) => `${timestamp},${kwh}`)].join('\n');

    const normalizedFile = new File([csv], `normalized-${file.name}`, { type: 'text/csv' });

    setUploading(true);
    try {
      const res = await api.uploadCsv(normalizedFile);
      setResult(res);
    } catch (err) {
      setResult({ status: 'error', message: err.message });
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreview(null);
    setMapping({ timestamp: '', kwh: '' });
    setResult(null);
    setParseError(null);
  };

  return (
    <div className="space-y-6 page-enter page-enter-active">
      <div>
        <h2 className="text-2xl font-bold text-white">Upload CSV</h2>
        <p className="text-sm text-slate-500 mt-1">Import smart meter data from CSV exports</p>
      </div>

      {!file && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`card border-2 border-dashed cursor-pointer transition-all duration-200 ${
            dragOver
              ? 'border-ww-blue-500 bg-ww-blue-500/5 shadow-glow'
              : 'border-slate-700 hover:border-slate-600'
          }`}
          onClick={() => document.getElementById('csv-input').click()}
        >
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
              <UploadIcon className={`w-8 h-8 ${dragOver ? 'text-ww-blue-400' : 'text-slate-500'}`} />
            </div>
            <p className="text-lg font-medium text-slate-300 mb-2">Drop your CSV file here</p>
            <p className="text-sm text-slate-500 mb-4">or click to browse</p>
            <div className="text-xs text-slate-600 space-y-1 text-center">
              <p>Accepted format: CSV with date-time and consumption columns</p>
              <p>
                Example: <code className="text-slate-500">timestamp,kwh</code> or{' '}
                <code className="text-slate-500">DateTime,Usage(kWh)</code>
              </p>
            </div>
          </div>
          <input
            id="csv-input"
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
        </div>
      )}

      {parseError && (
        <div className="card-compact border border-red-500/30 bg-red-500/10 text-sm text-red-300">
          {parseError}
        </div>
      )}

      {file && !result && (
        <div className="space-y-4">
          <div className="card flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-ww-blue-500/10 flex items-center justify-center">
              <FileText className="w-6 h-6 text-ww-blue-400" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-white">{file.name}</p>
              <p className="text-xs text-slate-500">
                {(file.size / 1024).toFixed(1)} KB
                {preview && ` - ${preview.totalRows.toLocaleString()} rows`}
              </p>
            </div>
            <button onClick={reset} className="text-slate-500 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {preview && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <h3 className="text-sm font-medium text-slate-400">Column Mapping</h3>
                <p className="text-xs text-slate-500">Map source columns to required schema</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1">
                  <span className="text-xs text-slate-500">Timestamp column</span>
                  <select
                    value={mapping.timestamp}
                    onChange={(e) => setMapping((m) => ({ ...m, timestamp: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
                  >
                    <option value="">Select column</option>
                    {preview.headers.map((header) => (
                      <option key={header} value={header}>{header}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-xs text-slate-500">kWh column</span>
                  <select
                    value={mapping.kwh}
                    onChange={(e) => setMapping((m) => ({ ...m, kwh: e.target.value }))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-ww-blue-500"
                  >
                    <option value="">Select column</option>
                    {preview.headers.map((header) => (
                      <option key={header} value={header}>{header}</option>
                    ))}
                  </select>
                </label>
              </div>

              <h3 className="text-sm font-medium text-slate-400">Mapped Data Preview</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">timestamp</th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">kwh</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mappedPreviewRows.map((row, index) => (
                      <tr key={`${row.timestamp}-${index}`} className="border-b border-slate-800/50">
                        <td className="py-2 px-3 text-slate-300 font-mono">{row.timestamp || '-'}</td>
                        <td className="py-2 px-3 text-slate-300 font-mono">{row.kwh || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {preview.totalRows > 10 && (
                <p className="text-xs text-slate-600">Showing 10 of {preview.totalRows.toLocaleString()} rows</p>
              )}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleUpload}
              disabled={uploading || !mapping.timestamp || !mapping.kwh}
              className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : `Import ${preview?.totalRows.toLocaleString() || ''} Readings`}
            </button>
            <button onClick={reset} className="btn-ghost">Cancel</button>
          </div>
        </div>
      )}

      {result && (
        <div className="card">
          {result.status === 'success' ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-emerald-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Import Successful</h3>
              <p className="text-sm text-slate-400 mb-1">
                {result.rows_imported.toLocaleString()} readings imported
              </p>
              {result.total_errors > 0 && (
                <p className="text-xs text-amber-400">
                  {result.total_errors} row{result.total_errors > 1 ? 's' : ''} skipped due to errors
                </p>
              )}
              <button onClick={reset} className="btn-primary mt-6">Upload Another</button>
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-red-400 mb-2">Upload Failed</h3>
              <p className="text-sm text-slate-400">{result.message}</p>
              <button onClick={reset} className="btn-primary mt-6">Try Again</button>
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h3 className="text-sm font-medium text-slate-400 mb-3">Expected CSV Format</h3>
        <div className="bg-slate-800 rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto">
          <p className="text-slate-500">timestamp,kwh</p>
          <p>2024-01-15T08:00:00,1.234</p>
          <p>2024-01-15T09:00:00,0.856</p>
          <p>2024-01-15T10:00:00,0.432</p>
        </div>
        <p className="text-xs text-slate-600 mt-3">
          You can upload non-standard headers and map them above before import.
        </p>
      </div>
    </div>
  );
}
