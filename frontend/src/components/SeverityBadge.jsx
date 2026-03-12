// Consistent inline-style palette — works with glass system, no Tailwind opacity conflicts
const SEV = {
  CRITICAL:  { bg: 'rgba(239,68,68,0.12)',    color: '#fca5a5', border: 'rgba(239,68,68,0.3)',    dot: '#f87171' },
  SEVERE:    { bg: 'rgba(239,68,68,0.12)',    color: '#fca5a5', border: 'rgba(239,68,68,0.3)',    dot: '#f87171' },
  HIGH:      { bg: 'rgba(249,115,22,0.12)',   color: '#fdba74', border: 'rgba(249,115,22,0.3)',   dot: '#fb923c' },
  MODERATE:  { bg: 'rgba(251,191,36,0.12)',   color: '#fde68a', border: 'rgba(251,191,36,0.3)',   dot: '#fbbf24' },
  MEDIUM:    { bg: 'rgba(251,191,36,0.12)',   color: '#fde68a', border: 'rgba(251,191,36,0.3)',   dot: '#fbbf24' },
  WARNING:   { bg: 'rgba(251,191,36,0.12)',   color: '#fde68a', border: 'rgba(251,191,36,0.3)',   dot: '#fbbf24' },
  MINOR:     { bg: 'rgba(251,191,36,0.08)',   color: '#fcd34d', border: 'rgba(251,191,36,0.2)',   dot: '#fbbf24' },
  LOW:       { bg: 'rgba(52,211,153,0.10)',   color: '#6ee7b7', border: 'rgba(52,211,153,0.25)',  dot: '#34d399' },
  NORMAL:    { bg: 'rgba(52,211,153,0.10)',   color: '#6ee7b7', border: 'rgba(52,211,153,0.25)',  dot: '#34d399' },
  INFO:      { bg: 'rgba(148,163,184,0.08)',  color: '#94a3b8', border: 'rgba(148,163,184,0.2)',  dot: '#64748b' },
  APPROVED:  { bg: 'rgba(52,211,153,0.10)',   color: '#6ee7b7', border: 'rgba(52,211,153,0.25)',  dot: '#34d399' },
  VALIDATED: { bg: 'rgba(52,211,153,0.10)',   color: '#6ee7b7', border: 'rgba(52,211,153,0.25)',  dot: '#34d399' },
  REJECTED:  { bg: 'rgba(239,68,68,0.12)',    color: '#fca5a5', border: 'rgba(239,68,68,0.3)',    dot: '#f87171' },
  CHALLENGED:{ bg: 'rgba(249,115,22,0.12)',   color: '#fdba74', border: 'rgba(249,115,22,0.3)',   dot: '#fb923c' },
  PENDING:   { bg: 'rgba(251,191,36,0.12)',   color: '#fde68a', border: 'rgba(251,191,36,0.3)',   dot: '#fbbf24' },
  ESCALATED: { bg: 'rgba(167,139,250,0.12)',  color: '#c4b5fd', border: 'rgba(167,139,250,0.3)',  dot: '#a78bfa' },
  APPROVED_WITH_CONDITIONS: { bg: 'rgba(34,211,238,0.10)', color: '#67e8f9', border: 'rgba(34,211,238,0.25)', dot: '#22d3ee' },
  DEFROSTING:{ bg: 'rgba(96,165,250,0.10)',   color: '#93c5fd', border: 'rgba(96,165,250,0.25)',  dot: '#60a5fa' },
  OFFLINE:   { bg: 'rgba(100,116,139,0.10)',  color: '#94a3b8', border: 'rgba(100,116,139,0.2)',  dot: '#64748b' },
}

export default function SeverityBadge({ label, showDot = true }) {
  const key = label?.toUpperCase().replace(/ /g, '_')
  const s = SEV[key] ?? SEV.INFO
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}
    >
      {showDot && (
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ background: s.dot, boxShadow: `0 0 4px ${s.dot}` }}
        />
      )}
      {label}
    </span>
  )
}

