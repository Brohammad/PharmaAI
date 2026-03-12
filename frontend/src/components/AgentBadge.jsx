// Distinct, non-clashing palette for each agent — inline styles for glass compatibility
const AGENT = {
  SENTINEL:   { bg: 'rgba(34,211,238,0.10)',  color: '#67e8f9', border: 'rgba(34,211,238,0.25)',  dot: '#22d3ee' },
  PULSE:      { bg: 'rgba(41,156,255,0.10)',  color: '#7dd3fc', border: 'rgba(41,156,255,0.25)',  dot: '#38bdf8' },
  AEGIS:      { bg: 'rgba(167,139,250,0.10)', color: '#c4b5fd', border: 'rgba(167,139,250,0.25)', dot: '#a78bfa' },
  MERIDIAN:   { bg: 'rgba(251,191,36,0.10)',  color: '#fcd34d', border: 'rgba(251,191,36,0.25)',  dot: '#fbbf24' },
  CRITIQUE:   { bg: 'rgba(249,115,22,0.10)',  color: '#fdba74', border: 'rgba(249,115,22,0.25)',  dot: '#fb923c' },
  COMPLIANCE: { bg: 'rgba(52,211,153,0.10)',  color: '#6ee7b7', border: 'rgba(52,211,153,0.25)',  dot: '#34d399' },
  NEXUS:      { bg: 'rgba(192,132,252,0.10)', color: '#e9d5ff', border: 'rgba(192,132,252,0.25)', dot: '#c084fc' },
  CHRONICLE:  { bg: 'rgba(148,163,184,0.08)', color: '#cbd5e1', border: 'rgba(148,163,184,0.2)',  dot: '#94a3b8' },
  EXECUTION:  { bg: 'rgba(41,156,255,0.08)',  color: '#93c5fd', border: 'rgba(41,156,255,0.2)',   dot: '#60a5fa' },
}

export default function AgentBadge({ agent, showDot = true, size = 'sm' }) {
  const key = agent?.toUpperCase()
  const s = AGENT[key] ?? { bg: 'rgba(100,116,139,0.1)', color: '#94a3b8', border: 'rgba(100,116,139,0.2)', dot: '#64748b' }
  const fontSize = size === 'xs' ? '10px' : '11px'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}`, fontSize }}
    >
      {showDot && (
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{ background: s.dot, boxShadow: `0 0 4px ${s.dot}` }}
        />
      )}
      {agent}
    </span>
  )
}

