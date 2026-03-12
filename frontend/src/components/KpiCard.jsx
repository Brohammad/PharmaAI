import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

const COLOR = {
  brand:   { accent: '#299cff', dimBg: 'rgba(41,156,255,0.08)',  border: 'rgba(41,156,255,0.2)',  text: '#51bdff',  glow: 'rgba(41,156,255,0.2)' },
  emerald: { accent: '#34d399', dimBg: 'rgba(52,211,153,0.08)',  border: 'rgba(52,211,153,0.2)',  text: '#6ee7b7',  glow: 'rgba(52,211,153,0.2)' },
  red:     { accent: '#f87171', dimBg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.2)', text: '#fca5a5',  glow: 'rgba(248,113,113,0.2)' },
  amber:   { accent: '#fbbf24', dimBg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.2)',  text: '#fcd34d',  glow: 'rgba(251,191,36,0.2)' },
  purple:  { accent: '#a78bfa', dimBg: 'rgba(167,139,250,0.08)', border: 'rgba(167,139,250,0.2)', text: '#c4b5fd',  glow: 'rgba(167,139,250,0.2)' },
  cyan:    { accent: '#22d3ee', dimBg: 'rgba(34,211,238,0.08)',  border: 'rgba(34,211,238,0.2)',  text: '#67e8f9',  glow: 'rgba(34,211,238,0.2)' },
}

export default function KpiCard({ label, value, unit = '', sub, trend, icon: Icon, color = 'brand', loading = false }) {
  const c = COLOR[color] ?? COLOR.brand

  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus
  const trendColor = trend > 0 ? '#34d399' : trend < 0 ? '#f87171' : '#64748b'
  const trendBg    = trend > 0 ? 'rgba(52,211,153,0.1)' : trend < 0 ? 'rgba(248,113,113,0.1)' : 'rgba(100,116,139,0.1)'

  if (loading) {
    return (
      <div className="glass p-5 overflow-hidden relative">
        <div className="skeleton h-3 w-2/3 mb-4" />
        <div className="skeleton h-8 w-1/2 mb-2" />
        <div className="skeleton h-2.5 w-3/4" />
      </div>
    )
  }

  return (
    <div
      className="relative overflow-hidden rounded-2xl p-5 group transition-all duration-300"
      style={{
        background: 'rgba(12, 18, 33, 0.6)',
        border: `1px solid ${c.border}`,
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        boxShadow: `0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)`,
      }}
    >
      {/* Subtle top-accent gradient wash */}
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${c.accent}60, transparent)` }}
      />
      {/* Background glow blob */}
      <div
        className="absolute -top-6 -right-6 w-20 h-20 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl"
        style={{ background: c.glow }}
      />

      {/* Header row */}
      <div className="flex items-start justify-between mb-4">
        <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'rgba(148,163,184,0.7)' }}>
          {label}
        </span>
        {Icon && (
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: c.dimBg, boxShadow: `0 0 12px ${c.glow}` }}
          >
            <Icon size={14} style={{ color: c.accent }} />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-1.5 mb-3">
        <span
          className="text-[28px] font-bold leading-none tabular-nums"
          style={{ color: c.text, textShadow: `0 0 20px ${c.glow}` }}
        >
          {value}
        </span>
        {unit && (
          <span className="text-sm mb-0.5 font-medium" style={{ color: 'rgba(148,163,184,0.6)' }}>
            {unit}
          </span>
        )}
      </div>

      {/* Bottom row — trend + sub */}
      {(sub !== undefined || trend !== undefined) && (
        <div className="flex items-center gap-2 flex-wrap">
          {trend !== undefined && (
            <span
              className="inline-flex items-center gap-0.5 text-[11px] font-semibold px-1.5 py-0.5 rounded-lg"
              style={{ color: trendColor, background: trendBg }}
            >
              <TrendIcon size={10} />
              {Math.abs(trend)}%
            </span>
          )}
          {sub && <span className="text-[11px]" style={{ color: 'rgba(100,116,139,0.8)' }}>{sub}</span>}
        </div>
      )}

      {/* Bottom accent bar */}
      <div
        className="absolute bottom-0 left-0 right-0 h-[2px] opacity-40 group-hover:opacity-80 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent 0%, ${c.accent} 50%, transparent 100%)` }}
      />
    </div>
  )
}
