import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, Cpu, AlertTriangle, TrendingUp, Upload, Zap, Activity,
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/devices', label: 'Devices', icon: Cpu },
  { to: '/anomalies', label: 'Anomalies', icon: AlertTriangle },
  { to: '/forecast', label: 'Forecast', icon: TrendingUp },
  { to: '/upload', label: 'Upload', icon: Upload },
];

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900/50 border-r border-slate-800 backdrop-blur-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
          <div className="relative">
            <Zap className="w-8 h-8 text-ww-blue-400" />
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-ww-amber-400 rounded-full animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-ww-blue-400 to-ww-amber-400 bg-clip-text text-transparent">
              WattWise
            </h1>
            <p className="text-[10px] text-slate-500 tracking-wider uppercase">Energy Analytics</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon className="w-5 h-5" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Status footer */}
        <div className="px-4 py-4 border-t border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>System Online</span>
          </div>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-800">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-ww-blue-400" />
            <span className="font-bold text-lg bg-gradient-to-r from-ww-blue-400 to-ww-amber-400 bg-clip-text text-transparent">
              WattWise
            </span>
          </div>
        </div>
        <nav className="flex overflow-x-auto px-2 pb-2 gap-1 scrollbar-hide">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-ww-blue-600/30 text-ww-blue-400 border border-ww-blue-500/30'
                    : 'text-slate-400 hover:text-slate-300'
                }`
              }
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto md:pt-0 pt-24">
        <div className="p-4 md:p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
