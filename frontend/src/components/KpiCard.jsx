import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function KpiCard({ label, value, unit = '', sub, trend, icon: Icon, color = 'brand', loading = false }) {
  const colorMap = {
    brand:   { bg: 'bg-brand-500/10',   border: 'border-brand-500/20',   icon: 'text-brand-400',   val: 'text-brand-300' },
    emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: 'text-emerald-400', val: 'text-emerald-300' },
    red:     { bg: 'bg-red-500/10',     border: 'border-red-500/20',     icon: 'text-red-400',     val: 'text-red-300' },
    amber:   { bg: 'bg-amber-500/10',   border: 'border-amber-500/20',   icon: 'text-amber-400',   val: 'text-amber-300' },
    purple:  { bg: 'bg-purple-500/10',  border: 'border-purple-500/20',  icon: 'text-purple-400',  val: 'text-purple-300' },
    cyan:    { bg: 'bg-cyan-500/10',    border: 'border-cyan-500/20',    icon: 'text-cyan-400',    val: 'text-cyan-300' },
  }
  const c = colorMap[color] ?? colorMap.brand

  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus
  const trendColor = trend > 0 ? 'text-emerald-400' : trend < 0 ? 'text-red-400' : 'text-slate-500'

  if (loading) {
    return (
      <div className={`card border ${c.border} p-5 animate-pulse`}>
        <div className="h-4 bg-slate-700 rounded w-2/3 mb-3" />
        <div className="h-8 bg-slate-700 rounded w-1/2 mb-2" />
        <div className="h-3 bg-slate-700 rounded w-3/4" />
      </div>
    )
  }

  return (
    <div className={`card border ${c.border} p-5 group hover:border-opacity-60 transition-all duration-200`}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
        {Icon && (
          <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center`}>
            <Icon size={15} className={c.icon} />
          </div>
        )}
      </div>

      <div className="flex items-end gap-1.5">
        <span className={`text-2xl font-bold ${c.val} leading-none tabular-nums`}>{value}</span>
        {unit && <span className="text-sm text-slate-400 mb-0.5 font-medium">{unit}</span>}
      </div>

      {(sub || trend !== undefined) && (
        <div className="mt-2 flex items-center gap-2">
          {trend !== undefined && (
            <span className={`flex items-center gap-0.5 text-xs font-semibold ${trendColor}`}>
              <TrendIcon size={11} />
              {Math.abs(trend)}%
            </span>
          )}
          {sub && <span className="text-xs text-slate-500">{sub}</span>}
        </div>
      )}
    </div>
  )
}
