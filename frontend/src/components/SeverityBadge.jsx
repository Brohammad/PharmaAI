// Muted inline-style palette — low saturation, comfortable on dark glass
const SEV = {
  CRITICAL:  { bg: 'rgba(239,68,68,0.08)',    color: '#e2a0a0', border: 'rgba(239,68,68,0.2)',    dot: '#ef4444' },
  SEVERE:    { bg: 'rgba(239,68,68,0.08)',    color: '#e2a0a0', border: 'rgba(239,68,68,0.2)',    dot: '#ef4444' },
  HIGH:      { bg: 'rgba(249,115,22,0.08)',   color: '#dba882', border: 'rgba(249,115,22,0.2)',   dot: '#f97316' },
  MODERATE:  { bg: 'rgba(234,179,8,0.08)',    color: '#c9b46a', border: 'rgba(234,179,8,0.2)',    dot: '#ca8a04' },
  MEDIUM:    { bg: 'rgba(234,179,8,0.08)',    color: '#c9b46a', border: 'rgba(234,179,8,0.2)',    dot: '#ca8a04' },
  WARNING:   { bg: 'rgba(234,179,8,0.08)',    color: '#c9b46a', border: 'rgba(234,179,8,0.2)',    dot: '#ca8a04' },
  MINOR:     { bg: 'rgba(234,179,8,0.06)',    color: '#b8a558', border: 'rgba(234,179,8,0.15)',   dot: '#a16207' },
  LOW:       { bg: 'rgba(34,197,94,0.07)',    color: '#86b89a', border: 'rgba(34,197,94,0.18)',   dot: '#22c55e' },
  NORMAL:    { bg: 'rgba(34,197,94,0.07)',    color: '#86b89a', border: 'rgba(34,197,94,0.18)',   dot: '#22c55e' },
  INFO:      { bg: 'rgba(148,163,184,0.06)',  color: '#7d8fa3', border: 'rgba(148,163,184,0.15)', dot: '#475569' },
  APPROVED:  { bg: 'rgba(34,197,94,0.07)',    color: '#86b89a', border: 'rgba(34,197,94,0.18)',   dot: '#22c55e' },
  VALIDATED: { bg: 'rgba(34,197,94,0.07)',    color: '#86b89a', border: 'rgba(34,197,94,0.18)',   dot: '#22c55e' },
  REJECTED:  { bg: 'rgba(239,68,68,0.08)',    color: '#e2a0a0', border: 'rgba(239,68,68,0.2)',    dot: '#ef4444' },
  CHALLENGED:{ bg: 'rgba(249,115,22,0.08)',   color: '#dba882', border: 'rgba(249,115,22,0.2)',   dot: '#f97316' },
  PENDING:   { bg: 'rgba(234,179,8,0.08)',    color: '#c9b46a', border: 'rgba(234,179,8,0.2)',    dot: '#ca8a04' },
  ESCALATED: { bg: 'rgba(139,92,246,0.08)',   color: '#a893cc', border: 'rgba(139,92,246,0.2)',   dot: '#7c3aed' },
  APPROVED_WITH_CONDITIONS: { bg: 'rgba(6,182,212,0.07)', color: '#7ab8c4', border: 'rgba(6,182,212,0.18)', dot: '#0891b2' },
  DEFROSTING:{ bg: 'rgba(59,130,246,0.08)',   color: '#7ea8cc', border: 'rgba(59,130,246,0.2)',   dot: '#3b82f6' },
  OFFLINE:   { bg: 'rgba(71,85,105,0.08)',    color: '#64748b', border: 'rgba(71,85,105,0.18)',   dot: '#334155' },
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

