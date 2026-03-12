const AGENT_META = {
  SENTINEL:   { bg: 'bg-cyan-500/15',    text: 'text-cyan-300',    border: 'border-cyan-500/30',    dot: 'bg-cyan-400' },
  PULSE:      { bg: 'bg-brand-500/15',   text: 'text-brand-300',   border: 'border-brand-500/30',   dot: 'bg-brand-400' },
  AEGIS:      { bg: 'bg-violet-500/15',  text: 'text-violet-300',  border: 'border-violet-500/30',  dot: 'bg-violet-400' },
  MERIDIAN:   { bg: 'bg-amber-500/15',   text: 'text-amber-300',   border: 'border-amber-500/30',   dot: 'bg-amber-400' },
  CRITIQUE:   { bg: 'bg-orange-500/15',  text: 'text-orange-300',  border: 'border-orange-500/30',  dot: 'bg-orange-400' },
  COMPLIANCE: { bg: 'bg-teal-500/15',    text: 'text-teal-300',    border: 'border-teal-500/30',    dot: 'bg-teal-400' },
  NEXUS:      { bg: 'bg-purple-500/15',  text: 'text-purple-300',  border: 'border-purple-500/30',  dot: 'bg-purple-400' },
  CHRONICLE:  { bg: 'bg-slate-500/15',   text: 'text-slate-300',   border: 'border-slate-500/30',   dot: 'bg-slate-400' },
}

export default function AgentBadge({ agent, showDot = true, size = 'sm' }) {
  const meta = AGENT_META[agent?.toUpperCase()] ?? {
    bg: 'bg-slate-600/20', text: 'text-slate-400', border: 'border-slate-600/30', dot: 'bg-slate-400',
  }
  const textSize = size === 'xs' ? 'text-[10px]' : 'text-xs'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold border ${textSize} ${meta.bg} ${meta.text} ${meta.border}`}>
      {showDot && <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />}
      {agent}
    </span>
  )
}
