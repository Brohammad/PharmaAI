import { useWebSocket } from '../api/client'
import AgentBadge from './AgentBadge'
import SeverityBadge from './SeverityBadge'
import { Radio } from 'lucide-react'

function timeAgo(ts) {
  if (!ts) return ''
  const diff = Math.floor((Date.now() - new Date(ts)) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function LiveFeed({ initialEvents = [] }) {
  const { messages, connected } = useWebSocket(40)

  // Merge WS messages with initial REST events, deduplicate
  const wsEvents = messages.filter((m) => m.type === 'agent_event').map((m) => m.data)
  const all = [...wsEvents, ...initialEvents].slice(0, 35)

  return (
    <div className="card flex flex-col h-full">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Radio size={15} className={connected ? 'text-emerald-400 animate-pulse' : 'text-slate-500'} />
          <span className="font-semibold text-slate-200 text-sm">Live Agent Feed</span>
        </div>
        <span className={`badge ${connected ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-slate-600/20 text-slate-500 border border-slate-600/30'}`}>
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-slate-700/30">
        {all.length === 0 && (
          <div className="px-5 py-8 text-center text-slate-500 text-sm">Waiting for events…</div>
        )}
        {all.map((evt, i) => (
          <div key={`${evt.agent}-${i}`} className="px-4 py-3 flex gap-3 items-start hover:bg-slate-700/20 transition-colors animate-fade-in">
            <div className="flex flex-col items-start gap-1.5 shrink-0 pt-0.5">
              <AgentBadge agent={evt.agent} size="xs" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-300 leading-snug">{evt.message || evt.description}</p>
              {evt.store_id && (
                <p className="text-xs text-slate-500 mt-0.5">{evt.store_id}{evt.zone && ` · ${evt.zone}`}</p>
              )}
            </div>
            <div className="flex flex-col items-end gap-1 shrink-0">
              <SeverityBadge label={evt.severity || 'INFO'} showDot={false} />
              <span className="text-[10px] text-slate-600">{timeAgo(evt.timestamp)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
