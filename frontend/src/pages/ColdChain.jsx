import { useState } from 'react'
import { useColdChain, useCCAlerts, useTempTrend } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { Thermometer, AlertTriangle, RefreshCw, CheckCircle2 } from 'lucide-react'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const STATUS_COLOR = {
  NORMAL:     { bg: 'bg-emerald-500',  border: 'border-emerald-600' },
  WARNING:    { bg: 'bg-amber-400',    border: 'border-amber-500' },
  CRITICAL:   { bg: 'bg-red-500',      border: 'border-red-600' },
  OFFLINE:    { bg: 'bg-slate-600',    border: 'border-slate-700' },
  DEFROSTING: { bg: 'bg-blue-400',     border: 'border-blue-500' },
}

function FridgeCell({ unit, selected, onClick }) {
  const s = STATUS_COLOR[unit.status] ?? STATUS_COLOR.NORMAL
  return (
    <button
      onClick={onClick}
      title={`${unit.unit_id}\n${unit.temperature?.toFixed(1)}°C — ${unit.status}`}
      className={`
        w-full aspect-square rounded-lg border-2 transition-all duration-150
        ${s.bg} ${s.border}
        ${selected ? 'ring-2 ring-white ring-offset-1 ring-offset-slate-900 scale-110 z-10 relative' : 'hover:scale-105 opacity-80 hover:opacity-100'}
      `}
    />
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-semibold">
          {p.name}: {p.value?.toFixed(2)}°C
        </p>
      ))}
    </div>
  )
}

function TempChart({ unitId }) {
  const { data, isLoading } = useTempTrend(unitId)
  if (isLoading) return <div className="h-48 flex items-center justify-center"><span className="text-slate-500 text-sm">Loading trend…</span></div>

  const trend = data?.trend ?? []
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={trend} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
        <defs>
          <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 10 }} interval={5} />
        <YAxis domain={[0, 12]} tick={{ fill: '#64748b', fontSize: 10 }} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={2}  stroke="#34d399" strokeDasharray="4 2" label={{ value: '2°C min', fill: '#34d399', fontSize: 10 }} />
        <ReferenceLine y={8}  stroke="#f59e0b" strokeDasharray="4 2" label={{ value: '8°C max', fill: '#f59e0b', fontSize: 10 }} />
        <Area dataKey="temperature" name="Temp" stroke="#3b82f6" fill="url(#tempGrad)" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default function ColdChain() {
  const [selectedUnit, setSelectedUnit] = useState(null)
  const { data: overview, isLoading: ovLoading, isError: ovError, refetch } = useColdChain()
  const { data: alertsData, isLoading: alLoading } = useCCAlerts()

  if (ovLoading) return <PageLoader />
  if (ovError) return <ErrorState message="Cold chain data unavailable" retry={refetch} />

  const units = overview?.units ?? []
  const alerts = alertsData?.alerts ?? []
  const selUnit = units.find((u) => u.unit_id === selectedUnit) ?? units[0]

  const counts = units.reduce((acc, u) => {
    acc[u.status] = (acc[u.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Cold Chain Monitoring</h1>
          <p className="text-sm text-slate-400 mt-0.5">SENTINEL Agent · {units.length} refrigeration units tracked</p>
        </div>
        <button onClick={refetch} className="btn-ghost gap-1.5">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Status bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {Object.entries({ NORMAL: 'emerald', WARNING: 'amber', CRITICAL: 'red', DEFROSTING: 'brand', OFFLINE: 'slate' }).map(([s, col]) => (
          <div key={s} className="card p-4 text-center">
            <p className="text-2xl font-bold text-slate-100 tabular-nums">{counts[s] ?? 0}</p>
            <SeverityBadge label={s} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Fridge heatmap grid */}
        <div className="xl:col-span-2 card">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <Thermometer size={15} className="text-brand-400" />
              <span className="font-semibold text-slate-200 text-sm">Refrigeration Unit Grid</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              {Object.entries({ NORMAL: '#22c55e', WARNING: '#f59e0b', CRITICAL: '#ef4444', OFFLINE: '#475569' }).map(([k, c]) => (
                <span key={k} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-sm" style={{ background: c }} />{k}
                </span>
              ))}
            </div>
          </div>
          <div className="p-4 grid gap-1.5" style={{ gridTemplateColumns: 'repeat(15, minmax(0, 1fr))' }}>
            {units.map((u) => (
              <FridgeCell
                key={u.unit_id}
                unit={u}
                selected={selectedUnit === u.unit_id}
                onClick={() => setSelectedUnit(u.unit_id === selectedUnit ? null : u.unit_id)}
              />
            ))}
          </div>
          <p className="px-4 pb-3 text-xs text-slate-500">Click a cell to inspect 24h temperature history</p>
        </div>

        {/* Right panel — selected unit + alerts */}
        <div className="space-y-4">
          {/* Unit detail */}
          <div className="card">
            <div className="card-header">
              <span className="font-semibold text-slate-200 text-sm">
                {selUnit ? selUnit.unit_id : 'Select a unit'}
              </span>
              {selUnit && <SeverityBadge label={selUnit.status} />}
            </div>
            {selUnit && (
              <div className="card-body space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-slate-800/60 p-3">
                    <p className="text-xs text-slate-400 mb-1">Current Temp</p>
                    <p className="text-2xl font-bold text-slate-100 tabular-nums">{selUnit.temperature?.toFixed(1)}°C</p>
                  </div>
                  <div className="rounded-lg bg-slate-800/60 p-3">
                    <p className="text-xs text-slate-400 mb-1">Sensor</p>
                    <p className="font-semibold text-slate-200">{selUnit.sensor_status ?? 'OK'}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-2">24h Temperature Trend</p>
                  <TempChart unitId={selUnit.unit_id} />
                </div>
              </div>
            )}
          </div>

          {/* Alerts */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center gap-2">
                <AlertTriangle size={15} className="text-amber-400" />
                <span className="font-semibold text-slate-200 text-sm">Active Excursion Alerts</span>
              </div>
              <span className="badge bg-red-500/15 text-red-300 border border-red-500/30">{alerts.length}</span>
            </div>
            <div className="divide-y divide-slate-700/30 max-h-64 overflow-y-auto">
              {alLoading && <div className="px-4 py-3 text-slate-500 text-sm">Loading…</div>}
              {!alLoading && alerts.length === 0 && (
                <div className="px-4 py-5 flex flex-col items-center gap-2">
                  <CheckCircle2 size={24} className="text-emerald-400" />
                  <p className="text-sm text-slate-400">No active alerts</p>
                </div>
              )}
              {alerts.map((a, i) => (
                <div key={i} className="px-4 py-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-200 text-sm">{a.unit_id}</span>
                    <SeverityBadge label={a.severity ?? 'HIGH'} />
                  </div>
                  <p className="text-xs text-slate-400">{a.description}</p>
                  {a.critique_verdict && (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-slate-500">CRITIQUE:</span>
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
  )
}
