import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/common/Layout';
import Dashboard from './pages/Dashboard';
import Devices from './pages/Devices';
import Anomalies from './pages/Anomalies';
import Forecast from './pages/Forecast';
import Upload from './pages/Upload';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/devices" element={<Devices />} />
        <Route path="/anomalies" element={<Anomalies />} />
        <Route path="/forecast" element={<Forecast />} />
        <Route path="/upload" element={<Upload />} />
      </Route>
    </Routes>
  );
}
