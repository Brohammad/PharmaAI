import { useState } from 'react'
import { useEpidemics, useForecast, useForecastChart } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { TrendingUp, AlertCircle, Activity, ChevronDown } from 'lucide-react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'

const DISEASE_COLOR = {
  Dengue: '#f97316', Influenza: '#3b82f6', Malaria: '#8b5cf6',
  Gastroenteritis: '#ec4899', Chikungunya: '#10b981', Norovirus: '#f59e0b',
}

function getDiseaseColor(name = '') {
  const entry = Object.entries(DISEASE_COLOR).find(([k]) => name.includes(k))
  return entry ? entry[1] : '#64748b'
}

function EpidemicCard({ signal }) {
  const conf  = Math.round((signal.confidence ?? 0) * 100)
  const color = getDiseaseColor(signal.disease)
  const urgency = conf >= 80 ? 'CRITICAL' : conf >= 60 ? 'HIGH' : 'MEDIUM'

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-bold text-slate-100">{signal.disease}</p>
          <p className="text-xs text-slate-400 mt-0.5">{signal.affected_zones?.join(', ')}</p>
        </div>
        <SeverityBadge label={urgency} />
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-400">Signal Confidence</span>
          <span className="text-sm font-bold tabular-nums" style={{ color }}>{conf}%</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-700">
          <div
            className="h-2 rounded-full transition-all duration-700"
            style={{ width: `${conf}%`, background: color }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg bg-slate-800/60 p-2">
          <p className="text-slate-500">Demand Multiplier</p>
          <p className="font-bold text-slate-100 mt-0.5">×{signal.demand_multiplier?.toFixed(2)}</p>
        </div>
        <div className="rounded-lg bg-slate-800/60 p-2">
          <p className="text-slate-500">Week Peak</p>
          <p className="font-bold text-slate-100 mt-0.5">Week {signal.peak_week ?? '?'}</p>
        </div>
      </div>

      {signal.key_drugs?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {signal.key_drugs.slice(0, 4).map((d) => (
            <span key={d} className="px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-300 text-[10px] font-medium border border-slate-600/40">{d}</span>
          ))}
        </div>
      )}
    </div>
  )
}

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-xs shadow-2xl min-w-[180px]">
      <p className="text-slate-300 font-semibold mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center justify-between gap-4 py-0.5">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-bold text-slate-100">{Math.round(p.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

export default function Demand() {
  const [storeId, setStoreId] = useState('STORE_DEL_001')
  const { data: epData, isLoading: epLoading, isError: epError } = useEpidemics()
  const { data: fcData, isLoading: fcLoading } = useForecast(storeId)
  const { data: chartData, isLoading: chartLoading } = useForecastChart()

  if (epLoading) return <PageLoader />
  if (epError) return <ErrorState message="Demand intelligence unavailable" />

  const signals = epData?.signals ?? []
  const forecasts = fcData?.forecasts ?? []
  const chart = chartData?.data ?? []

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Demand Intelligence</h1>
          <p className="text-sm text-slate-400 mt-0.5">PULSE Agent · Epidemic-adjusted forecasting</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">Store</span>
          <div className="relative">
            <select
              className="appearance-none pl-3 pr-8 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm focus:outline-none focus:border-brand-500"
              value={storeId}
              onChange={(e) => setStoreId(e.target.value)}
            >
              {['STORE_DEL_001','STORE_DEL_042','STORE_MUM_007','STORE_BLR_023','STORE_CHE_015'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2 top-2 text-slate-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Epidemic signal cards */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle size={15} className="text-amber-400" />
          <h2 className="font-semibold text-slate-200 text-sm">Active Epidemic Signals</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {signals.map((s, i) => <EpidemicCard key={i} signal={s} />)}
        </div>
      </div>

      {/* Forecast chart */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <TrendingUp size={15} className="text-brand-400" />
            <span className="font-semibold text-slate-200 text-sm">28-Day Demand Forecast — Scenario Bands</span>
          </div>
          <span className="badge bg-brand-500/15 text-brand-300 border border-brand-500/30 text-xs">Epidemic-Adjusted</span>
        </div>
        <div className="card-body" style={{ height: 340 }}>
          {chartLoading ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">Loading chart…</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chart} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <defs>
                  <linearGradient id="epidHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="baseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} interval={3} />
                <YAxis tick={{ fill: '#64748b', fontSize: 10 }} />
                <Tooltip content={<ChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8', paddingTop: '12px' }} />
                <Area dataKey="epidemic_high"       name="Epidemic High"     stroke="#f97316" fill="url(#epidHigh)"  strokeWidth={1.5} dot={false} strokeDasharray="5 3" />
                <Area dataKey="baseline"            name="Baseline Forecast" stroke="#3b82f6" fill="url(#baseGrad)" strokeWidth={2}   dot={false} />
                <Line dataKey="epidemic_weighted"   name="Epidemic Weighted" stroke="#a78bfa" strokeWidth={2.5} dot={false} />
                <Line dataKey="historic_avg"        name="Historic Average"  stroke="#94a3b8" strokeWidth={1}   dot={false} strokeDasharray="4 2" />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* SKU forecast table */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Activity size={15} className="text-brand-400" />
            <span className="font-semibold text-slate-200 text-sm">SKU-Level Forecast — {storeId}</span>
          </div>
          <span className="text-xs text-slate-400">{forecasts.length} SKUs</span>
        </div>
        {fcLoading ? (
          <div className="px-5 py-8 text-center text-slate-500 text-sm">Loading forecasts…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>SKU</th><th>Drug Name</th><th>Category</th>
                  <th>Baseline Demand</th><th>Epidemic Adj.</th><th>Final Forecast</th>
                  <th>Confidence</th><th>Recommended Action</th>
                </tr>
              </thead>
              <tbody>
                {forecasts.map((f, i) => {
                  const conf = Math.round((f.confidence ?? 0.8) * 100)
                  const confColor = conf >= 85 ? 'text-emerald-400' : conf >= 70 ? 'text-amber-400' : 'text-red-400'
                  return (
                    <tr key={i}>
                      <td className="font-mono text-xs text-slate-300">{f.sku_id}</td>
                      <td className="font-medium text-slate-200">{f.drug_name}</td>
                      <td><SeverityBadge label={f.category ?? 'OTC'} showDot={false} /></td>
                      <td className="tabular-nums">{f.baseline_demand?.toLocaleString()}</td>
                      <td className="tabular-nums text-amber-300">×{f.epidemic_adjustment?.toFixed(2) ?? '1.00'}</td>
                      <td className="tabular-nums font-bold text-slate-100">{f.adjusted_forecast?.toLocaleString()}</td>
                      <td className={`tabular-nums font-semibold ${confColor}`}>{conf}%</td>
                      <td className="text-xs text-slate-400">{f.recommended_action ?? 'Monitor'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
