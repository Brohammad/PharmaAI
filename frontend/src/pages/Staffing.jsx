import { useStaffing } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { Users, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

function UtilBar({ label, value, max = 100, color }) {
  const pct = Math.min(Math.round((value / max) * 100), 100)
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-semibold tabular-nums" style={{ color }}>{value} / {max}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-slate-700">
        <div className="h-2 rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

const BarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-slate-300 font-semibold mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.fill }}>{p.name}: <b>{p.value}%</b></p>
      ))}
    </div>
  )
}

export default function Staffing() {
  const { data, isLoading, isError, refetch } = useStaffing()

  if (isLoading) return <PageLoader />
  if (isError) return <ErrorState message="Staffing data unavailable" retry={refetch} />

  const gaps = data?.active_gaps ?? []
  const zones = data?.zone_utilisation ?? []
  const coverage = data?.pharmacist_coverage_pct ?? 94
  const schedHComp = data?.schedule_h_compliance_pct ?? 98
  const activeShifts = data?.active_shifts ?? 0
  const nightGaps = data?.night_shift_gaps ?? 0

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Staffing Intelligence</h1>
        <p className="text-sm text-slate-400 mt-0.5">AEGIS Agent · Pharmacist coverage & Schedule H compliance</p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Pharmacist Coverage', value: `${coverage}%`, color: coverage >= 90 ? 'text-emerald-300' : 'text-red-300', icon: Users },
          { label: 'Schedule H Compliance', value: `${schedHComp}%`, color: schedHComp >= 95 ? 'text-emerald-300' : 'text-amber-300', icon: CheckCircle2 },
          { label: 'Active Shifts', value: activeShifts, color: 'text-brand-300', icon: Clock },
          { label: 'Night Shift Gaps', value: nightGaps, color: nightGaps > 0 ? 'text-red-300' : 'text-emerald-300', icon: AlertCircle },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{label}</span>
              <Icon size={15} className="text-slate-500" />
            </div>
            <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Zone utilisation chart */}
        <div className="card">
          <div className="card-header">
            <span className="font-semibold text-slate-200 text-sm">Zone Pharmacist Utilisation</span>
          </div>
          <div className="card-body" style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={zones} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="zone" tick={{ fill: '#64748b', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} unit="%" />
                <Tooltip content={<BarTooltip />} />
                <Bar dataKey="utilisation_pct" name="Utilisation" radius={[4, 4, 0, 0]}>
                  {zones.map((z, i) => (
                    <Cell key={i} fill={z.utilisation_pct >= 90 ? '#ef4444' : z.utilisation_pct >= 75 ? '#f59e0b' : '#34d399'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Active gaps */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <AlertCircle size={15} className="text-amber-400" />
              <span className="font-semibold text-slate-200 text-sm">Coverage Gaps</span>
            </div>
            <span className="badge bg-amber-500/15 text-amber-300 border border-amber-500/30">{gaps.length} active</span>
          </div>
          <div className="divide-y divide-slate-700/30 max-h-72 overflow-y-auto">
            {gaps.length === 0 && (
              <div className="px-4 py-6 flex flex-col items-center gap-2">
                <CheckCircle2 size={22} className="text-emerald-400" />
                <p className="text-sm text-slate-400">All shifts covered</p>
              </div>
            )}
            {gaps.map((g, i) => (
              <div key={i} className="px-4 py-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-200 text-sm">{g.store_id}</span>
                  <SeverityBadge label={g.severity ?? 'HIGH'} />
                </div>
                <p className="text-xs text-slate-400">{g.shift} shift · {g.gap_hours}h uncovered</p>
                {g.suggested_action && (
                  <p className="text-xs text-brand-400">→ {g.suggested_action}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Utilisation bars per zone */}
      {zones.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="font-semibold text-slate-200 text-sm">Pharmacist Load by Zone</span>
          </div>
          <div className="card-body space-y-4">
            {zones.map((z) => (
              <UtilBar
                key={z.zone}
                label={z.zone}
                value={z.utilisation_pct}
                max={100}
                color={z.utilisation_pct >= 90 ? '#ef4444' : z.utilisation_pct >= 75 ? '#f59e0b' : '#34d399'}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
