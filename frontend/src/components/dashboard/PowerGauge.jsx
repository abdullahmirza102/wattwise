import { useState, useEffect, useRef } from 'react';
import { formatWatts } from '../../utils/format';

export default function PowerGauge({ watts, connected }) {
  const [animatedWatts, setAnimatedWatts] = useState(0);
  const prevWatts = useRef(0);

  useEffect(() => {
    if (watts == null) return;
    const start = prevWatts.current;
    const end = watts;
    const duration = 1000;
    const startTime = performance.now();

    function animate(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedWatts(start + (end - start) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
    prevWatts.current = end;
  }, [watts]);

  const maxWatts = 15000;
  const percentage = Math.min((animatedWatts / maxWatts) * 100, 100);
  const angle = (percentage / 100) * 240 - 120; // -120 to +120 degrees

  // SVG arc for the gauge
  const radius = 80;
  const cx = 100;
  const cy = 100;
  const startAngle = -210;
  const endAngle = 30;
  const totalArc = endAngle - startAngle;
  const currentArc = startAngle + (percentage / 100) * totalArc;

  function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(cx, cy, r, startA, endA) {
    const start = polarToCartesian(cx, cy, r, endA);
    const end = polarToCartesian(cx, cy, r, startA);
    const largeArc = endA - startA > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
  }

  const getColor = () => {
    if (percentage < 30) return '#22c55e';
    if (percentage < 60) return '#3b82f6';
    if (percentage < 80) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="card flex flex-col items-center py-6">
      <div className="flex items-center gap-2 mb-4">
        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
        <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">
          {connected ? 'Live Power' : 'Connecting...'}
        </span>
      </div>

      <svg width="200" height="140" viewBox="0 0 200 150">
        {/* Background arc */}
        <path
          d={describeArc(cx, cy, radius, startAngle, endAngle)}
          fill="none"
          stroke="#1e293b"
          strokeWidth="12"
          strokeLinecap="round"
        />
        {/* Active arc */}
        {percentage > 0 && (
          <path
            d={describeArc(cx, cy, radius, startAngle, currentArc)}
            fill="none"
            stroke={getColor()}
            strokeWidth="12"
            strokeLinecap="round"
            style={{
              filter: `drop-shadow(0 0 8px ${getColor()}40)`,
              transition: 'd 0.5s ease-out',
            }}
          />
        )}
        {/* Tick marks */}
        {[0, 25, 50, 75, 100].map((pct) => {
          const tickAngle = startAngle + (pct / 100) * totalArc;
          const inner = polarToCartesian(cx, cy, radius - 16, tickAngle);
          const outer = polarToCartesian(cx, cy, radius - 8, tickAngle);
          return (
            <line
              key={pct}
              x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y}
              stroke="#475569" strokeWidth="1.5"
            />
          );
        })}
      </svg>

      <div className="text-center -mt-4">
        <span className="text-3xl font-bold text-white font-mono">
          {formatWatts(animatedWatts)}
        </span>
        <p className="text-xs text-slate-500 mt-1">Current whole-home draw</p>
      </div>

      {/* Scale labels */}
      <div className="flex justify-between w-48 mt-2 text-[10px] text-slate-600">
        <span>0W</span>
        <span>7.5kW</span>
        <span>15kW</span>
      </div>
    </div>
  );
}
