import { useWebSocket } from '../api/client'
import AgentBadge from './AgentBadge'
import SeverityBadge from './SeverityBadge'
import { Radio, Wifi, WifiOff } from 'lucide-react'

/* ── Helpers ──────────────────────────────────────────────────── */
function timeAgo(ts) {
  if (!ts) return ''
  const diff = Math.floor((Date.now() - new Date(ts)) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

/**
 * Parse a raw event message into { title, detail }
 * Cleans up the raw "[Live Cycle] AGENT — node 'x' complete" noise
 * and extracts meaningful store/drug/unit context.
 */
function parseMessage(evt) {
  const raw = evt.message || evt.description || ''

  // [Live Cycle] AGENT — node 'x' complete  →  compact display
  const cycleMatch = raw.match(/\[Live Cycle\]\s+(\w+)\s+[—-]+\s+node\s+'([^']+)'\s+complete/i)
  if (cycleMatch) {
    return { title: `Node '${cycleMatch[2]}' completed`, detail: null, isSystem: true }
  }

  // SEVERE/MODERATE excursion at STORE_XXX — UNIT → temp
  const excursionMatch = raw.match(/(SEVERE|MODERATE|CRITICAL|MINOR)\s+excursion\s+at\s+(STORE_\w+)\s+[—-]+\s+(\w+)\s+[→→]\s+([\d.]+°C)/i)
  if (excursionMatch) {
    return {
      title: `${excursionMatch[3]} — ${excursionMatch[4]}`,
      detail: excursionMatch[2],
    }
  }

  // Generic: cap title at ~60 chars, put rest as detail
  if (raw.length > 65) {
    const breakIdx = raw.indexOf(' ', 55)
    return {
      title: raw.slice(0, breakIdx > 0 ? breakIdx : 60) + '…',
      detail: evt.store_id || null,
    }
  }
  return { title: raw, detail: evt.store_id || null }
}

/* Severity → left-border accent colour */
const SEV_ACCENT = {
  CRITICAL: '#f87171',
  SEVERE:   '#f87171',
  HIGH:     '#fb923c',
  MODERATE: '#fbbf24',
  MEDIUM:   '#fbbf24',
  WARNING:  '#fbbf24',
  MINOR:    '#fbbf24',
  LOW:      '#34d399',
  INFO:     'rgba(148,163,184,0.3)',
}

export default function LiveFeed({ initialEvents = [] }) {
  const { messages, connected } = useWebSocket(40)

  const wsEvents = messages.filter((m) => m.type === 'agent_event').map((m) => m.data)
  const all = [...wsEvents, ...initialEvents].slice(0, 35)

  return (
    <div className="glass flex flex-col h-full">
      {/* Header */}
      <div className="card-header">
        <div className="flex items-center gap-2">
          {connected
            ? <Radio size={14} className="text-emerald-400 animate-pulse" />
            : <WifiOff size={14} className="text-slate-500" />
          }
          <span className="text-sm font-semibold text-slate-200">Live Agent Feed</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-600">{all.length} events</span>
          <span
            className="text-[10px] font-bold px-2 py-0.5 rounded-full"
            style={connected
              ? { background: 'rgba(52,211,153,0.12)', color: '#6ee7b7', border: '1px solid rgba(52,211,153,0.25)' }
              : { background: 'rgba(100,116,139,0.1)',  color: '#64748b', border: '1px solid rgba(100,116,139,0.2)' }
            }
          >
            {connected ? '● LIVE' : '○ OFFLINE'}
          </span>
        </div>
      </div>

      {/* Feed rows */}
      <div className="flex-1 overflow-y-auto">
        {all.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
            <Wifi size={28} className="opacity-30" />
            <p className="text-sm">Waiting for events…</p>
          </div>
        )}
        {all.map((evt, i) => {
          const { title, detail, isSystem } = parseMessage(evt)
          const sev = (evt.severity || 'INFO').toUpperCase()
          const accent = SEV_ACCENT[sev] ?? SEV_ACCENT.INFO

          return (
            <div
              key={`${evt.agent}-${i}`}
              className="relative flex gap-3 px-4 py-2.5 transition-colors duration-150 animate-fade-in"
              style={{
                borderBottom: '1px solid rgba(255,255,255,0.03)',
                borderLeft: `2px solid ${accent}`,
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              {/* Agent badge */}
              <div className="shrink-0 pt-0.5">
                <AgentBadge agent={evt.agent} size="xs" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p
                  className="text-[13px] leading-snug truncate"
                  style={{ color: isSystem ? 'rgba(148,163,184,0.6)' : '#cbd5e1' }}
                  title={evt.message || evt.description}
                >
                  {title}
                </p>
                {detail && (
                  <p className="text-[11px] mt-0.5 font-mono" style={{ color: 'rgba(100,116,139,0.8)' }}>
                    {detail}
                    {evt.zone ? ` · ${evt.zone}` : ''}
                  </p>
                )}
              </div>

              {/* Right side */}
              <div className="shrink-0 flex flex-col items-end gap-1 pt-0.5">
                <SeverityBadge label={sev} showDot={false} />
                <span className="text-[10px]" style={{ color: 'rgba(100,116,139,0.6)' }}>
                  {timeAgo(evt.timestamp)}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

