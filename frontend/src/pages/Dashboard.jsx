import { useKPIs, useEvents, useWebSocket } from '../api/client'
import KpiCard from '../components/KpiCard'
import LiveFeed from '../components/LiveFeed'
import AgentBadge from '../components/AgentBadge'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import {
  Store, AlertTriangle, Thermometer, TrendingUp, Users, Package,
  Activity, Brain, Clock, CheckCircle2, XCircle, Zap,
} from 'lucide-react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Area, AreaChart,
} from 'recharts'

const AGENTS = ['SENTINEL', 'PULSE', 'AEGIS', 'MERIDIAN', 'CRITIQUE', 'COMPLIANCE', 'NEXUS', 'CHRONICLE']

function SystemHealthRing({ value, label, color }) {
  const r = 36
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - value / 100)
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg viewBox="0 0 88 88" className="w-full h-full -rotate-90">
          <circle cx="44" cy="44" r={r} fill="none" stroke="#1e293b" strokeWidth="7" />
          <circle
            cx="44" cy="44" r={r} fill="none"
            stroke={color} strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-base font-bold text-slate-100">
          {value}%
        </span>
      </div>
      <span className="text-xs text-slate-400 text-center">{label}</span>
    </div>
  )
}

function AgentStatusStrip() {
  const { messages } = useWebSocket()
  // Track which agents have recent activity (last 60s)
  const recentAgents = new Set(
    messages
      .filter((m) => m.type === 'agent_event' && m.data?.agent)
      .slice(0, 20)
      .map((m) => m.data.agent?.toUpperCase())
  )

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Activity size={15} className="text-brand-400" />
          <span className="font-semibold text-slate-200 text-sm">Agent Status</span>
        </div>
        <span className="badge bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-xs">
          All Operational
        </span>
      </div>
      <div className="card-body grid grid-cols-4 gap-2">
        {AGENTS.map((agent) => {
          const active = recentAgents.has(agent)
          return (
            <div key={agent} className="flex flex-col items-center gap-2 p-3 rounded-xl bg-slate-800/40 border border-slate-700/30">
              <div className={`w-3 h-3 rounded-full ${active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
              <AgentBadge agent={agent} size="xs" showDot={false} />
              <span className="text-[10px] text-slate-500">{active ? 'Active' : 'Idle'}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: kpis, isLoading: kpiLoading, isError: kpiError, refetch: kpiRefetch } = useKPIs()
  const { data: eventsData, isLoading: eventsLoading } = useEvents(25)

  if (kpiError) return <ErrorState message="Could not reach backend" retry={kpiRefetch} />

  const events = eventsData?.events ?? []

  const kpiDefs = [
    { key: 'stores_online',        label: 'Stores Online',         icon: Store,        color: 'emerald', unit: '',  trendKey: null },
    { key: 'active_alerts',        label: 'Active Alerts',         icon: AlertTriangle, color: 'red',    unit: '',  trendKey: null },
    { key: 'cold_chain_risk_pct',  label: 'Cold Chain Risk',       icon: Thermometer,  color: 'amber',  unit: '%', trendKey: null },
    { key: 'schedule_h_compliance', label: 'Schedule H Compliance', icon: CheckCircle2, color: 'emerald', unit: '%', trendKey: null },
    { key: 'demand_mape',          label: 'Demand MAPE',           icon: TrendingUp,   color: 'brand',  unit: '%', trendKey: null },
    { key: 'active_escalations',   label: 'Escalations Pending',   icon: Brain,        color: 'purple', unit: '',  trendKey: null },
    { key: 'pharmacist_coverage',  label: 'Pharmacist Coverage',   icon: Users,        color: 'cyan',   unit: '%', trendKey: null },
    { key: 'expiry_risk_units',    label: 'Expiry Risk Items',     icon: Package,      color: 'amber',  unit: '',  trendKey: null },
    { key: 'cycles_today',         label: 'Cycles Today',          icon: Zap,          color: 'brand',  unit: '',  trendKey: null },
    { key: 'decisions_approved',   label: 'Decisions Approved',    icon: CheckCircle2, color: 'emerald', unit: '', trendKey: null },
    { key: 'decisions_escalated',  label: 'Decisions Escalated',   icon: XCircle,      color: 'purple', unit: '',  trendKey: null },
    { key: 'avg_cycle_time_s',     label: 'Avg Cycle Time',        icon: Clock,        color: 'cyan',   unit: 's', trendKey: null },
  ]

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Operations Dashboard</h1>
          <p className="text-sm text-slate-400 mt-0.5">MedChain India · 320 Pharmacies · Real-time intelligence</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-emerald-300">System Nominal</span>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {kpiDefs.map(({ key, label, icon, color, unit }) => (
          <KpiCard
            key={key}
            label={label}
            value={kpis?.[key] ?? '—'}
            unit={unit}
            icon={icon}
            color={color}
            loading={kpiLoading}
          />
        ))}
      </div>

      {/* System health rings + agent strip */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card col-span-1">
          <div className="card-header">
            <span className="font-semibold text-slate-200 text-sm">System Health</span>
          </div>
          <div className="card-body flex justify-around py-6">
            <SystemHealthRing value={kpis?.pharmacist_coverage ?? 94} label="Staffing" color="#34d399" />
            <SystemHealthRing value={kpis?.schedule_h_compliance ?? 98} label="Compliance" color="#60a5fa" />
            <SystemHealthRing value={Math.round((1 - (kpis?.cold_chain_risk_pct ?? 4) / 100) * 100)} label="Cold Chain" color="#a78bfa" />
          </div>
        </div>

        <div className="lg:col-span-2">
          <AgentStatusStrip />
        </div>
      </div>

      {/* Live Feed + mini radar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Live feed — tall */}
        <div className="lg:col-span-2 h-[460px]">
          <LiveFeed initialEvents={eventsLoading ? [] : events} />
        </div>

        {/* Agent activity radar */}
        <div className="card">
          <div className="card-header">
            <span className="font-semibold text-slate-200 text-sm">Agent Activity</span>
          </div>
          <div className="card-body flex items-center justify-center" style={{ height: 380 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart
                data={[
                  { agent: 'SENTINEL', value: 82 },
                  { agent: 'PULSE',    value: 91 },
                  { agent: 'AEGIS',    value: 73 },
                  { agent: 'MERIDIAN', value: 88 },
                  { agent: 'CRITIQUE', value: 65 },
                  { agent: 'COMPLIANCE', value: 77 },
                  { agent: 'NEXUS',    value: 95 },
                  { agent: 'CHRONICLE', value: 60 },
                ]}
              >
                <PolarGrid stroke="#1e293b" />
                <PolarAngleAxis dataKey="agent" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} dot={{ r: 3, fill: '#3b82f6' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
