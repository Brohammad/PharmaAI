const SEV_META = {
  CRITICAL: { bg: 'bg-red-500/15',     text: 'text-red-300',     border: 'border-red-500/30',     dot: 'bg-red-400' },
  HIGH:     { bg: 'bg-orange-500/15',  text: 'text-orange-300',  border: 'border-orange-500/30',  dot: 'bg-orange-400' },
  MEDIUM:   { bg: 'bg-amber-500/15',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400' },
  LOW:      { bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  INFO:     { bg: 'bg-slate-500/15',   text: 'text-slate-400',   border: 'border-slate-600/30',   dot: 'bg-slate-500' },
  APPROVED: { bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/30', dot: 'bg-emerald-400' },
  REJECTED: { bg: 'bg-red-500/15',     text: 'text-red-300',     border: 'border-red-500/30',     dot: 'bg-red-400' },
  PENDING:  { bg: 'bg-amber-500/15',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400' },
  ESCALATED:{ bg: 'bg-purple-500/15',  text: 'text-purple-300',  border: 'border-purple-500/30',  dot: 'bg-purple-400' },
  APPROVED_WITH_CONDITIONS: { bg: 'bg-cyan-500/15', text: 'text-cyan-300', border: 'border-cyan-500/30', dot: 'bg-cyan-400' },
}

export default function SeverityBadge({ label, showDot = true }) {
  const key = label?.toUpperCase().replace(/ /g, '_')
  const meta = SEV_META[key] ?? SEV_META.INFO
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${meta.bg} ${meta.text} ${meta.border}`}>
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />}
      {label}
    </span>
  )
}
