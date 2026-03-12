export function Skeleton({ className = '', lines = 1 }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton h-4 rounded" style={{ width: `${80 - i * 15}%` }} />
      ))}
    </div>
  );
}

export function CardSkeleton({ className = '' }) {
  return (
    <div className={`card animate-pulse ${className}`}>
      <div className="skeleton h-4 w-1/3 mb-4 rounded" />
      <div className="skeleton h-8 w-2/3 mb-2 rounded" />
      <div className="skeleton h-3 w-1/2 rounded" />
    </div>
  );
}

export function ChartSkeleton({ className = '' }) {
  return (
    <div className={`card animate-pulse ${className}`}>
      <div className="skeleton h-4 w-1/4 mb-6 rounded" />
      <div className="flex items-end gap-2 h-48">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="skeleton flex-1 rounded-t"
            style={{ height: `${30 + Math.random() * 70}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-slate-500" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-slate-300 mb-2">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md mb-4">{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
        <span className="text-3xl">!</span>
      </div>
      <h3 className="text-lg font-semibold text-red-400 mb-2">Something went wrong</h3>
      <p className="text-sm text-slate-500 max-w-md mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-primary">
          Try Again
        </button>
      )}
    </div>
  );
}
