import { useState } from 'react'
import { useColdChain, useCCAlerts, useTempTrend } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { Thermometer, AlertTriangle, RefreshCw, CheckCircle2, Droplets, DoorOpen } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

/* ── Status colour map — covers all statuses the API returns ── */
const STATUS_STYLE = {
  NORMAL:     { bg: '#22c55e', border: '#16a34a', glow: 'rgba(34,197,94,0.5)' },
  MINOR:      { bg: '#f59e0b', border: '#d97706', glow: 'rgba(245,158,11,0.5)' },
  MODERATE:   { bg: '#f97316', border: '#ea580c', glow: 'rgba(249,115,22,0.5)' },
  WARNING:    { bg: '#f59e0b', border: '#d97706', glow: 'rgba(245,158,11,0.5)' },
  CRITICAL:   { bg: '#ef4444', border: '#dc2626', glow: 'rgba(239,68,68,0.6)' },
  DEFROSTING: { bg: '#60a5fa', border: '#3b82f6', glow: 'rgba(96,165,250,0.4)' },
  OFFLINE:    { bg: '#475569', border: '#334155', glow: 'rgba(71,85,105,0.3)' },
}

/* ── Fridge Cell ──────────────────────────────────────────────── */
function FridgeCell({ unit, selected, onClick }) {
  const s = STATUS_STYLE[unit.status] ?? STATUS_STYLE.NORMAL
  const temp = unit.temperature_c ?? unit.temperature
  return (
    <button
      onClick={onClick}
      title={`${unit.unit_id} @ ${unit.store_id}\n${temp?.toFixed(1)}°C — ${unit.status}`}
      className="w-full aspect-square rounded-lg transition-all duration-150"
      style={{
        background: s.bg,
        border: `2px solid ${s.border}`,
        boxShadow: selected
          ? `0 0 0 2px #fff, 0 0 12px ${s.glow}`
          : `0 0 6px ${s.glow}`,
        transform: selected ? 'scale(1.15)' : 'scale(1)',
        opacity: selected ? 1 : 0.78,
        position: selected ? 'relative' : 'static',
        zIndex: selected ? 10 : 1,
      }}
      onMouseEnter={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = selected ? 'scale(1.15)' : 'scale(1.07)' }}
      onMouseLeave={e => { e.currentTarget.style.opacity = selected ? '1' : '0.78'; e.currentTarget.style.transform = selected ? 'scale(1.15)' : 'scale(1)' }}
    />
  )
}

/* ── Tooltip ──────────────────────────────────────────────────── */
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-xl px-3 py-2 text-xs shadow-2xl"
      style={{ background: 'rgba(10,16,30,0.95)', border: '1px solid rgba(255,255,255,0.1)' }}
    >
      <p className="text-slate-400 mb-1.5 font-mono">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="font-semibold" style={{ color: p.color }}>
          {p.name}: {p.value?.toFixed(2)}°C
        </p>
      ))}
    </div>
  )
}

/* ── Temp Chart ───────────────────────────────────────────────── */
function TempChart({ unitId }) {
  const { data, isLoading } = useTempTrend(unitId)

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="flex gap-1 items-end">
          {[3,5,4,6,4,5,3].map((h,i) => (
            <div key={i} className="skeleton rounded-sm w-2" style={{ height: `${h*8}px` }} />
          ))}
        </div>
      </div>
    )
  }

  const raw = data?.trend ?? []
  // Format ISO timestamps → HH:MM for a clean X-axis
  const trend = raw.map((pt) => ({
    ...pt,
    timeLabel: pt.time ? new Date(pt.time).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) : '',
  }))

  // Sample every ~6th point if dense (> 100 pts) to keep chart clean
  const display = trend.length > 100 ? trend.filter((_, i) => i % 6 === 0) : trend

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={display} margin={{ top: 5, right: 8, bottom: 0, left: -18 }}>
        <defs>
          <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.35} />
            <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="timeLabel"
          tick={{ fill: '#475569', fontSize: 9 }}
          interval={Math.floor(display.length / 6)}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={['auto', 'auto']}
          tick={{ fill: '#475569', fontSize: 9 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<ChartTooltip />} />
        <ReferenceLine y={2} stroke="#34d399" strokeDasharray="4 2"
          label={{ value: '2°C', fill: '#34d399', fontSize: 9, position: 'right' }} />
        <ReferenceLine y={8} stroke="#f59e0b" strokeDasharray="4 2"
          label={{ value: '8°C', fill: '#f59e0b', fontSize: 9, position: 'right' }} />
        <Area
          dataKey="temperature_c"
          name="Temp"
          stroke="#38bdf8"
          fill="url(#tempGrad)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 3, fill: '#38bdf8', strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

/* ── Legend dot ───────────────────────────────────────────────── */
function LegendDot({ status }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.NORMAL
  return (
    <span className="flex items-center gap-1.5 text-[11px]" style={{ color: 'rgba(148,163,184,0.7)' }}>
      <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.bg, boxShadow: `0 0 4px ${s.glow}` }} />
      {status}
    </span>
  )
}

/* ── Page ─────────────────────────────────────────────────────── */
export default function ColdChain() {
  const [selectedUnit, setSelectedUnit] = useState(null)
  const { data: overview, isLoading: ovLoading, isError: ovError, refetch } = useColdChain()
  const { data: alertsData, isLoading: alLoading } = useCCAlerts()

  if (ovLoading) return <PageLoader />
  if (ovError)   return <ErrorState message="Cold chain data unavailable" retry={refetch} />

  const units  = overview?.units ?? []
  const alerts = alertsData?.alerts ?? []

  // Selected unit: fall back to first unit
  const selUnit = units.find((u) => u.unit_id === selectedUnit) ?? units[0]

  // Count by status
  const counts = units.reduce((acc, u) => {
    acc[u.status] = (acc[u.status] ?? 0) + 1
    return acc
  }, {})

  const statusOrder = ['NORMAL', 'MINOR', 'MODERATE', 'CRITICAL', 'DEFROSTING', 'OFFLINE']

  return (
    <div className="relative">
      <div
        className="absolute inset-x-0 top-0 h-48 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 70% 50% at 50% -10%, rgba(56,189,248,0.1) 0%, transparent 70%)' }}
      />

      <div className="relative page">
        {/* ── Header ─────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-gradient text-2xl font-bold tracking-tight">Cold Chain Monitoring</h1>
            <p className="text-slate-500 text-sm mt-1">SENTINEL Agent · {units.length} refrigeration units tracked</p>
          </div>
          <button onClick={refetch} className="btn-ghost gap-1.5">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {/* ── Status summary bar ─────────────────────────── */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
          {statusOrder.map((s) => {
            const st = STATUS_STYLE[s]
            return (
              <div
                key={s}
                className="relative overflow-hidden rounded-2xl p-4 text-center"
                style={{
                  background: 'rgba(10,16,30,0.6)',
                  border: `1px solid ${st.border}30`,
                  backdropFilter: 'blur(12px)',
                }}
              >
                <div
                  className="absolute inset-x-0 top-0 h-0.5"
                  style={{ background: `linear-gradient(90deg, transparent, ${st.bg}, transparent)` }}
                />
                <p className="text-2xl font-bold tabular-nums" style={{ color: st.bg, textShadow: `0 0 16px ${st.glow}` }}>
                  {counts[s] ?? 0}
                </p>
                <p className="text-[10px] font-semibold mt-1" style={{ color: 'rgba(148,163,184,0.6)' }}>{s}</p>
              </div>
            )
          })}
        </div>

        {/* ── Main grid ──────────────────────────────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* Fridge heatmap */}
          <div className="xl:col-span-2 glass">
            <div className="card-header">
              <div className="flex items-center gap-2">
                <Thermometer size={14} className="text-cyan-400" />
                <span className="text-sm font-semibold text-slate-200">Refrigeration Unit Grid</span>
              </div>
              <div className="flex items-center gap-3">
                {['NORMAL','MINOR','MODERATE','CRITICAL','OFFLINE'].map((s) => <LegendDot key={s} status={s} />)}
              </div>
            </div>
            <div className="p-4 grid gap-1.5" style={{ gridTemplateColumns: 'repeat(15, minmax(0, 1fr))' }}>
              {units.map((u) => (
                <FridgeCell
                  key={`${u.store_id}-${u.unit_id}`}
                  unit={u}
                  selected={selUnit?.unit_id === u.unit_id && selUnit?.store_id === u.store_id}
                  onClick={() => {
                    const id = `${u.store_id}::${u.unit_id}`
                    setSelectedUnit(prev => prev === id ? null : id)
                  }}
                />
              ))}
            </div>
            <p className="px-4 pb-3 text-[11px]" style={{ color: 'rgba(100,116,139,0.6)' }}>
              Click a cell to inspect 24 h temperature history
            </p>
          </div>

          {/* Right panel */}
          <div className="space-y-4">

            {/* Unit detail */}
            <div className="glass">
              <div className="card-header">
                <div>
                  <span className="text-sm font-semibold text-slate-200">
                    {selUnit?.unit_id ?? 'Select a unit'}
                  </span>
                  {selUnit?.store_id && (
                    <p className="text-[11px] font-mono mt-0.5" style={{ color: 'rgba(100,116,139,0.7)' }}>
                      {selUnit.store_id}
                    </p>
                  )}
                </div>
                {selUnit && <SeverityBadge label={selUnit.status} />}
              </div>

              {selUnit && (
                <div className="card-body space-y-4">
                  {/* Stat mini-cards */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="glass-panel p-3 text-center">
                      <Thermometer size={12} className="text-cyan-400 mx-auto mb-1" />
                      <p className="text-[11px] text-slate-500 mb-0.5">Temp</p>
                      <p className="text-lg font-bold tabular-nums text-slate-100">
                        {(selUnit.temperature_c ?? selUnit.temperature)?.toFixed(1)}°C
                      </p>
                    </div>
                    <div className="glass-panel p-3 text-center">
                      <Droplets size={12} className="text-blue-400 mx-auto mb-1" />
                      <p className="text-[11px] text-slate-500 mb-0.5">Humidity</p>
                      <p className="text-lg font-bold tabular-nums text-slate-100">
                        {selUnit.humidity_pct?.toFixed(0) ?? '—'}%
                      </p>
                    </div>
                    <div className="glass-panel p-3 text-center">
                      <DoorOpen size={12} className="text-slate-400 mx-auto mb-1" />
                      <p className="text-[11px] text-slate-500 mb-0.5">Door</p>
                      <p className="text-sm font-bold" style={{ color: selUnit.door_open ? '#f87171' : '#34d399' }}>
                        {selUnit.door_open ? 'OPEN' : 'CLOSED'}
                      </p>
                    </div>
                  </div>

                  {/* Trend */}
                  <div>
                    <p className="text-[11px] font-semibold text-slate-400 mb-2">24 h Temperature Trend</p>
                    <TempChart unitId={selUnit.unit_id} />
                  </div>
                </div>
              )}
            </div>

            {/* Alerts */}
            <div className="glass">
              <div className="card-header">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={13} className="text-amber-400" />
                  <span className="text-sm font-semibold text-slate-200">Active Excursion Alerts</span>
                </div>
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full tabular-nums"
                  style={{ background: 'rgba(239,68,68,0.12)', color: '#fca5a5', border: '1px solid rgba(239,68,68,0.25)' }}
                >
                  {alerts.length}
                </span>
              </div>
              <div className="divide-y max-h-64 overflow-y-auto" style={{ borderColor: 'rgba(255,255,255,0.03)' }}>
                {alLoading && <div className="px-4 py-3 text-slate-500 text-sm">Loading…</div>}
                {!alLoading && alerts.length === 0 && (
                  <div className="px-4 py-6 flex flex-col items-center gap-2">
                    <CheckCircle2 size={22} className="text-emerald-400" />
                    <p className="text-sm text-slate-400">No active alerts</p>
                  </div>
                )}
                {alerts.map((a, i) => (
                  <div key={i} className="px-4 py-3 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-slate-200 text-sm">{a.unit_id}</span>
                        <span className="text-[11px] font-mono ml-2" style={{ color: 'rgba(100,116,139,0.7)' }}>
                          {a.store_id}
                        </span>
                      </div>
                      <SeverityBadge label={a.severity ?? 'HIGH'} />
                    </div>
                    <p className="text-[12px]" style={{ color: 'rgba(148,163,184,0.8)' }}>{a.description}</p>
                    {a.critique_verdict && (
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-600">CRITIQUE</span>
                        <SeverityBadge label={a.critique_verdict} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

