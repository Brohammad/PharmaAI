export default function LoadingSpinner({ size = 'md', className = '' }) {
  const s = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }[size] ?? 'w-6 h-6'
  return (
    <div className={`${s} border-2 border-slate-600 border-t-brand-400 rounded-full animate-spin ${className}`} />
  )
}

export function PageLoader() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <LoadingSpinner size="lg" />
      <p className="text-slate-500 text-sm">Loading data…</p>
    </div>
  )
}

export function ErrorState({ message = 'Failed to load data', retry }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
        <span className="text-xl">⚠</span>
      </div>
      <p className="text-slate-400 text-sm">{message}</p>
      {retry && (
        <button onClick={retry} className="btn-ghost text-xs">Retry</button>
      )}
    </div>
  )
}
