import { useKPIs, useEvents, useWebSocket } from '../api/client'
import { useAuth } from '../api/auth'
import KpiCard from '../components/KpiCard'
import LiveFeed from '../components/LiveFeed'
import AgentBadge from '../components/AgentBadge'
import CycleRunner from '../components/CycleRunner'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import {
  Store, AlertTriangle, Thermometer, TrendingUp, Users, Package,
  Activity, Brain, Clock, CheckCircle2, XCircle, Zap, LogOut, Shield,
} from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts'

const AGENTS = ['SENTINEL', 'PULSE', 'AEGIS', 'MERIDIAN', 'CRITIQUE', 'COMPLIANCE', 'NEXUS', 'CHRONICLE']

/* ── System Health Ring ────────────────────────────────────────── */
function HealthRing({ value, label, color, trackColor = 'rgba(255,255,255,0.05)' }) {
  const r = 34
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - value / 100)
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-[76px] h-[76px]">
        {/* Outer glow */}
        <div
          className="absolute inset-0 rounded-full blur-lg opacity-30 animate-glow-pulse"
          style={{ background: color }}
        />
        <svg viewBox="0 0 76 76" className="w-full h-full -rotate-90 relative">
          <circle cx="38" cy="38" r={r} fill="none" stroke={trackColor} strokeWidth="5" />
          <circle
            cx="38" cy="38" r={r} fill="none"
            stroke={color} strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.16,1,0.3,1)', filter: `drop-shadow(0 0 4px ${color})` }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-slate-100 tabular-nums">
          {value}%
        </span>
      </div>
      <span className="text-[11px] font-medium text-slate-400">{label}</span>
    </div>
  )
}

/* ── Agent Status ──────────────────────────────────────────────── */
function AgentStrip() {
  const { messages } = useWebSocket()
  const recentAgents = new Set(
    messages
      .filter((m) => m.type === 'agent_event' && m.data?.agent)
      .slice(0, 20)
      .map((m) => m.data.agent?.toUpperCase())
  )

  return (
    <div className="glass">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-brand-400" />
          <span className="text-sm font-semibold text-slate-200">Agent Status</span>
        </div>
        <span
          className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
          style={{ background: 'rgba(52,211,153,0.12)', color: '#6ee7b7', border: '1px solid rgba(52,211,153,0.25)' }}
        >
          All Operational
        </span>
      </div>
      <div className="card-body grid grid-cols-4 gap-2">
        {AGENTS.map((agent) => {
          const active = recentAgents.has(agent)
          return (
            <div
              key={agent}
              className="flex flex-col items-center gap-2 py-3 rounded-xl transition-all duration-200"
              style={{
                background: active ? 'rgba(52,211,153,0.06)' : 'rgba(255,255,255,0.02)',
                border: `1px solid ${active ? 'rgba(52,211,153,0.2)' : 'rgba(255,255,255,0.05)'}`,
              }}
            >
              <div
                className={`w-2 h-2 rounded-full ${active ? 'animate-pulse' : ''}`}
                style={{
                  background: active ? '#34d399' : 'rgba(148,163,184,0.3)',
                  boxShadow: active ? '0 0 6px #34d399' : 'none',
                }}
              />
              <AgentBadge agent={agent} size="xs" showDot={false} />
              <span className="text-[9px] font-medium" style={{ color: active ? '#86efac' : 'rgba(100,116,139,0.7)' }}>
                {active ? 'Active' : 'Idle'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Dashboard ─────────────────────────────────────────────────── */
export default function Dashboard() {
  const { data: kpis, isLoading: kpiLoading, isError: kpiError, refetch: kpiRefetch } = useKPIs()
  const { data: eventsData, isLoading: eventsLoading } = useEvents(25)
  const { user, logout } = useAuth()

  if (kpiError) return <ErrorState message="Could not reach backend" retry={kpiRefetch} />

  const events = eventsData?.events ?? []

  const kpiDefs = [
    { key: 'stores_online',         label: 'Stores Online',         icon: Store,         color: 'emerald', unit: '' },
    { key: 'active_alerts',         label: 'Active Alerts',         icon: AlertTriangle, color: 'red',     unit: '' },
    { key: 'cold_chain_risk_pct',   label: 'Cold Chain Risk',       icon: Thermometer,   color: 'amber',   unit: '%' },
    { key: 'schedule_h_compliance', label: 'H Compliance',          icon: CheckCircle2,  color: 'emerald', unit: '%' },
    { key: 'demand_mape',           label: 'Demand MAPE',           icon: TrendingUp,    color: 'brand',   unit: '%' },
    { key: 'active_escalations',    label: 'Escalations',           icon: Brain,         color: 'purple',  unit: '' },
    { key: 'pharmacist_coverage',   label: 'Staff Coverage',        icon: Users,         color: 'cyan',    unit: '%' },
    { key: 'expiry_risk_units',     label: 'Expiry Risk',           icon: Package,       color: 'amber',   unit: '' },
    { key: 'cycles_today',          label: 'Cycles Today',          icon: Zap,           color: 'brand',   unit: '' },
    { key: 'decisions_approved',    label: 'Approved',              icon: CheckCircle2,  color: 'emerald', unit: '' },
    { key: 'decisions_escalated',   label: 'Escalated',             icon: XCircle,       color: 'purple',  unit: '' },
    { key: 'avg_cycle_time_s',      label: 'Avg Cycle Time',        icon: Clock,         color: 'cyan',    unit: 's' },
  ]

  return (
    <div className="relative min-h-full">
      {/* Hero gradient wash behind header */}
      <div
        className="absolute inset-x-0 top-0 h-64 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(14,126,246,0.18) 0%, transparent 70%)' }}
      />

      <div className="relative page">
        {/* ── Header ───────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-gradient text-2xl font-bold leading-tight tracking-tight">Operations Dashboard</h1>
            <p className="text-slate-500 text-sm mt-1">MedChain India · 320 Pharmacies · Real-time intelligence</p>
          </div>
          <div className="flex items-center gap-3">
            {/* System status pill */}
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full"
              style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ boxShadow: '0 0 6px #34d399' }} />
              <span className="text-xs font-semibold text-emerald-300">System Nominal</span>
            </div>
            {/* User pill */}
            {user && (
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-full"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                <Shield size={11} className="text-brand-400" />
                <span className="text-xs text-slate-300 font-medium">{user.full_name}</span>
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
                  style={{ background: 'rgba(41,156,255,0.15)', color: '#51bdff' }}
                >
                  {user.role}
                </span>
                <button onClick={logout} className="text-slate-600 hover:text-red-400 transition-colors ml-0.5" title="Sign out">
                  <LogOut size={10} />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── KPI Grid ─────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
          {kpiDefs.map(({ key, label, icon, color, unit }) => (
            <KpiCard
              key={key} label={label}
              value={kpis?.[key] ?? '—'} unit={unit}
              icon={icon} color={color} loading={kpiLoading}
            />
          ))}
        </div>

        {/* ── System Health + Agent Strip ───────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* Health rings */}
          <div className="glass lg:col-span-2">
            <div className="card-header">
              <span className="text-sm font-semibold text-slate-200">System Health</span>
            </div>
            <div className="card-body flex justify-around py-6">
              <HealthRing value={kpis?.pharmacist_coverage ?? 94}  label="Staffing"    color="#34d399" />
              <HealthRing value={kpis?.schedule_h_compliance ?? 98} label="Compliance"  color="#60a5fa" />
              <HealthRing
                value={Math.round((1 - (kpis?.cold_chain_risk_pct ?? 4) / 100) * 100)}
                label="Cold Chain" color="#a78bfa"
              />
            </div>
          </div>
          {/* Agent strip */}
          <div className="lg:col-span-3">
            <AgentStrip />
          </div>
        </div>

        {/* ── Cycle Runner ─────────────────────────────────── */}
        <CycleRunner />

        {/* ── Live Feed + Radar ─────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 h-[440px]">
            <LiveFeed initialEvents={eventsLoading ? [] : events} />
          </div>

          <div className="glass flex flex-col">
            <div className="card-header">
              <span className="text-sm font-semibold text-slate-200">Agent Activity</span>
              <span className="text-[10px] text-slate-600 font-medium">Load distribution</span>
            </div>
            <div className="flex-1 flex items-center justify-center p-4">
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart
                  data={[
                    { agent: 'SENTINEL',   value: 82 },
                    { agent: 'PULSE',      value: 91 },
                    { agent: 'AEGIS',      value: 73 },
                    { agent: 'MERIDIAN',   value: 88 },
                    { agent: 'CRITIQUE',   value: 65 },
                    { agent: 'COMPLIANCE', value: 77 },
                    { agent: 'NEXUS',      value: 95 },
                    { agent: 'CHRONICLE',  value: 60 },
                  ]}
                >
                  <PolarGrid stroke="rgba(255,255,255,0.06)" />
                  <PolarAngleAxis dataKey="agent" tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }} />
                  <Radar
                    dataKey="value"
                    stroke="#299cff"
                    fill="#299cff"
                    fillOpacity={0.12}
                    dot={{ r: 3, fill: '#299cff', strokeWidth: 0 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

