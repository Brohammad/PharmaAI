// Muted per-agent palette — distinct hues, low saturation, comfortable on dark glass
const AGENT = {
  SENTINEL:   { bg: 'rgba(6,182,212,0.07)',   color: '#6eaeba',  border: 'rgba(6,182,212,0.18)',   dot: '#0891b2' },
  PULSE:      { bg: 'rgba(41,156,255,0.07)',  color: '#7499b8',  border: 'rgba(41,156,255,0.18)',  dot: '#2563eb' },
  AEGIS:      { bg: 'rgba(139,92,246,0.07)',  color: '#9d88bc',  border: 'rgba(139,92,246,0.18)',  dot: '#7c3aed' },
  MERIDIAN:   { bg: 'rgba(234,179,8,0.07)',   color: '#b8a050',  border: 'rgba(234,179,8,0.18)',   dot: '#a16207' },
  CRITIQUE:   { bg: 'rgba(249,115,22,0.07)',  color: '#c49070',  border: 'rgba(249,115,22,0.18)',  dot: '#c2410c' },
  COMPLIANCE: { bg: 'rgba(34,197,94,0.07)',   color: '#74a882',  border: 'rgba(34,197,94,0.18)',   dot: '#15803d' },
  NEXUS:      { bg: 'rgba(168,85,247,0.07)',  color: '#a888bf',  border: 'rgba(168,85,247,0.18)',  dot: '#9333ea' },
  CHRONICLE:  { bg: 'rgba(100,116,139,0.07)', color: '#6b7f96',  border: 'rgba(100,116,139,0.18)', dot: '#475569' },
  EXECUTION:  { bg: 'rgba(41,156,255,0.06)',  color: '#6e8eaa',  border: 'rgba(41,156,255,0.16)',  dot: '#1d4ed8' },
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

