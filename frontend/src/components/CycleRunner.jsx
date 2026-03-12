/**
 * PharmaIQ – Live Cycle Runner Panel
 *
 * Triggers a real LangGraph decision cycle via SSE and visualises
 * each agent node completing in real time. Shows a progress rail,
 * agent cards activating sequentially, and the final duration.
 */
import { useState, useRef, useCallback } from 'react'
import { Zap, Loader2, CheckCircle2, XCircle, Play, StopCircle } from 'lucide-react'
import AgentBadge from './AgentBadge'

const AGENT_ORDER = [
  'CHRONICLE_ENTRY',
  'SENTINEL',
  'PULSE',
  'AEGIS',
  'MERIDIAN',
  'CRITIQUE',
  'COMPLIANCE',
  'NEXUS',
  'EXECUTION',
  'CHRONICLE_EXIT',
]

const CYCLE_TYPES = [
  { value: 'MORNING_FORECAST',  label: 'Morning Forecast' },
  { value: 'COMPLIANCE_SWEEP',  label: 'Compliance Sweep' },
  { value: 'EXPIRY_REVIEW',     label: 'Expiry Review' },
  { value: 'MIDDAY_REFORECAST', label: 'Midday Reforecast' },
]

export default function CycleRunner() {
  const [cycleType, setCycleType]     = useState('MORNING_FORECAST')
  const [storeId, setStoreId]         = useState('STORE_DEL_007')
  const [running, setRunning]         = useState(false)
  const [completed, setCompleted]     = useState(false)
  const [error, setError]             = useState(null)
  const [runId, setRunId]             = useState(null)
  const [duration, setDuration]       = useState(null)
  const [completedNodes, setCompletedNodes] = useState(new Set())
  const [activeNode, setActiveNode]   = useState(null)
  const [events, setEvents]           = useState([])
  const esRef = useRef(null)

  const startCycle = useCallback(() => {
    if (running) return
    setRunning(true)
    setCompleted(false)
    setError(null)
    setRunId(null)
    setDuration(null)
    setCompletedNodes(new Set())
    setActiveNode(null)
    setEvents([])

    const url = `/api/v1/cycles/stream?store_id=${storeId}&cycle_type=${cycleType}&zone_id=DELHI_NCR`
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (evt) => {
      if (evt.data === '[DONE]') {
        es.close()
        setRunning(false)
        return
      }
      try {
        const msg = JSON.parse(evt.data)
        setEvents(prev => [...prev.slice(-29), msg])

        if (msg.type === 'cycle_start') {
          setRunId(msg.run_id)
        }
        if (msg.type === 'agent_progress') {
          const node = msg.node?.toUpperCase()
          setActiveNode(node)
          setCompletedNodes(prev => new Set([...prev, node]))
        }
        if (msg.type === 'cycle_complete') {
          setDuration(msg.duration_seconds)
          setCompleted(true)
          setActiveNode(null)
          setRunning(false)
          es.close()
        }
        if (msg.type === 'cycle_error') {
          setError(msg.error || 'Cycle failed')
          setRunning(false)
          es.close()
        }
      } catch { /* skip */ }
    }

    es.onerror = () => {
      setError('Connection lost. Is the backend running?')
      setRunning(false)
      es.close()
    }
  }, [cycleType, storeId, running])

  const stopCycle = useCallback(() => {
    esRef.current?.close()
    setRunning(false)
  }, [])

  const progressPct = completedNodes.size > 0
    ? Math.round((completedNodes.size / AGENT_ORDER.length) * 100)
    : 0

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Zap size={15} className="text-brand-400" />
          <span className="font-semibold text-slate-200 text-sm">Live Cycle Runner</span>
          {running && (
            <span className="flex items-center gap-1 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/25 px-2 py-0.5 rounded-full">
              <Loader2 size={10} className="animate-spin" /> Running
            </span>
          )}
          {completed && !running && (
            <span className="flex items-center gap-1 text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={10} /> Done in {duration}s
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Controls */}
          <select
            value={storeId}
            onChange={e => setStoreId(e.target.value)}
            disabled={running}
            className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2 py-1 focus:outline-none disabled:opacity-50"
          >
            {['STORE_DEL_007','STORE_MUM_042','STORE_BLR_011','MEDCHAIN_HQ'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            value={cycleType}
            onChange={e => setCycleType(e.target.value)}
            disabled={running}
            className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2 py-1 focus:outline-none disabled:opacity-50"
          >
            {CYCLE_TYPES.map(c => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          {!running ? (
            <button
              onClick={startCycle}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-lg transition"
            >
              <Play size={11} /> Run
            </button>
          ) : (
            <button
              onClick={stopCycle}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/70 hover:bg-red-600 text-white text-xs font-semibold rounded-lg transition"
            >
              <StopCircle size={11} /> Stop
            </button>
          )}
        </div>
      </div>

      <div className="card-body space-y-4">
        {/* Progress bar */}
        {(running || completed) && (
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Pipeline progress</span>
              <span>{progressPct}%</span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-600 to-brand-400 rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {runId && (
              <p className="text-[10px] text-slate-600 mt-1 font-mono">run_id: {runId}</p>
            )}
          </div>
        )}

        {/* Agent progress rail */}
        <div className="grid grid-cols-5 gap-2">
          {AGENT_ORDER.map((node) => {
            const isComplete = completedNodes.has(node)
            const isActive   = activeNode === node
            const agentName  = node.replace('_ENTRY', '').replace('_EXIT', '')
            return (
              <div
                key={node}
                className={`flex flex-col items-center gap-1.5 p-2 rounded-xl border transition-all duration-300 ${
                  isComplete
                    ? 'bg-brand-500/10 border-brand-500/30'
                    : isActive
                    ? 'bg-amber-500/10 border-amber-500/30 animate-pulse'
                    : 'bg-slate-800/30 border-slate-700/30'
                }`}
              >
                <div className="relative">
                  {isActive && (
                    <div className="absolute -inset-1 rounded-full bg-amber-400/20 animate-ping" />
                  )}
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center ${
                    isComplete ? 'bg-brand-500/30' : isActive ? 'bg-amber-500/30' : 'bg-slate-700'
                  }`}>
                    {isComplete
                      ? <CheckCircle2 size={11} className="text-brand-400" />
                      : isActive
                      ? <Loader2 size={11} className="text-amber-400 animate-spin" />
                      : <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                    }
                  </div>
                </div>
                <AgentBadge agent={agentName} size="xs" showDot={false} />
              </div>
            )
          })}
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
            <XCircle size={13} />
            {error}
          </div>
        )}

        {/* Live events log */}
        {events.length > 0 && (
          <div className="bg-slate-950/60 rounded-xl border border-slate-800 p-3 max-h-32 overflow-y-auto">
            <p className="text-[10px] text-slate-600 font-mono mb-2">SSE event stream</p>
            {[...events].reverse().map((evt, i) => (
              <div key={i} className="text-[10px] font-mono text-slate-500 leading-5">
                <span className="text-brand-600">{evt.type}</span>
                {evt.agent && <span className="text-emerald-600 ml-2">{evt.agent}</span>}
                {evt.node  && <span className="text-slate-600 ml-1">→ {evt.node}</span>}
                {evt.duration_seconds && <span className="text-amber-500 ml-2">{evt.duration_seconds}s</span>}
              </div>
            ))}
          </div>
        )}

        {/* Idle state */}
        {!running && !completed && events.length === 0 && (
          <div className="text-center py-4">
            <p className="text-xs text-slate-500">
              Select a store and cycle type, then click <strong className="text-slate-400">Run</strong> to
              execute a real LangGraph decision cycle and watch all 8 agents complete in sequence.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
