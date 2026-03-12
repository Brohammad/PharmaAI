import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Thermometer, TrendingUp, Users,
  Package, Brain, Activity, ChevronRight, Zap, Truck, Radio,
} from 'lucide-react'

const NAV = [
  { to: '/',              icon: LayoutDashboard, label: 'Dashboard',    sub: 'Overview & KPIs' },
  { to: '/cold-chain',    icon: Thermometer,     label: 'Cold Chain',   sub: 'SENTINEL' },
  { to: '/demand',        icon: TrendingUp,      label: 'Demand Intel', sub: 'PULSE' },
  { to: '/staffing',      icon: Users,           label: 'Staffing',     sub: 'AEGIS' },
  { to: '/inventory',     icon: Package,         label: 'Inventory',    sub: 'MERIDIAN' },
  { to: '/supply-chain',  icon: Truck,           label: 'Supply Chain', sub: 'Stock & Transfers' },
  { to: '/decisions',     icon: Brain,           label: 'Decisions',    sub: 'NEXUS' },
]

export default function Sidebar({ wsConnected }) {
  return (
    <aside
      className="w-[220px] shrink-0 flex flex-col h-screen sticky top-0 z-40"
      style={{
        background: 'rgba(7, 13, 26, 0.85)',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
      }}
    >
      {/* ── Logo ────────────────────────────────────────────── */}
      <div className="px-4 py-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          {/* Icon with animated glow ring */}
          <div className="relative">
            <div className="absolute inset-0 rounded-xl blur-md opacity-60 animate-glow-pulse"
              style={{ background: 'linear-gradient(135deg, #299cff, #0a66e3)' }} />
            <div className="relative w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #299cff, #0a66e3)', boxShadow: '0 4px 15px rgba(41,156,255,0.35)' }}>
              <Activity size={17} className="text-white" />
            </div>
          </div>
          <div>
            <p className="text-gradient font-bold text-[15px] leading-none tracking-tight">PharmaIQ</p>
            <p className="text-slate-500 text-[11px] mt-0.5 font-medium">MedChain India</p>
          </div>
        </div>
      </div>

      {/* ── Nav ─────────────────────────────────────────────── */}
      <nav className="flex-1 px-2.5 py-3 space-y-0.5 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label, sub }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `group relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                isActive ? 'active-nav' : 'text-slate-400 hover:text-slate-100'
              }`
            }
            style={({ isActive }) => isActive ? {
              background: 'linear-gradient(135deg, rgba(41,156,255,0.15), rgba(10,102,227,0.08))',
              border: '1px solid rgba(41,156,255,0.25)',
              boxShadow: '0 2px 12px rgba(41,156,255,0.12), inset 0 1px 0 rgba(255,255,255,0.06)',
            } : {
              background: 'transparent',
              border: '1px solid transparent',
            }}
          >
            {({ isActive }) => (
              <>
                {/* Active glow streak */}
                {isActive && (
                  <span
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                    style={{ background: 'linear-gradient(to bottom, #51bdff, #0a66e3)' }}
                  />
                )}
                <Icon
                  size={16}
                  className={isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300 transition-colors'}
                />
                <span className="flex-1 min-w-0">
                  <span className={`block font-medium leading-none text-[13px] ${isActive ? 'text-slate-100' : ''}`}>
                    {label}
                  </span>
                  <span className="block text-[10px] mt-0.5 truncate"
                    style={{ color: isActive ? 'rgba(41,156,255,0.7)' : 'rgba(148,163,184,0.5)' }}>
                    {sub}
                  </span>
                </span>
                {isActive && (
                  <ChevronRight size={12} className="text-brand-400/60 shrink-0" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── Footer ──────────────────────────────────────────── */}
      <div className="px-4 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="glass-panel px-3 py-2.5 flex items-center gap-2">
          <Radio
            size={12}
            className={wsConnected ? 'text-emerald-400 animate-pulse' : 'text-slate-600'}
          />
          <span className={`text-[11px] font-medium flex-1 ${wsConnected ? 'text-emerald-300' : 'text-slate-500'}`}>
            {wsConnected ? 'Live feed active' : 'Reconnecting…'}
          </span>
          <span className="text-[10px] text-slate-600">8 agents</span>
        </div>
        <p className="text-[10px] text-slate-700 mt-2 text-center">PharmaIQ v2.0 · 320 stores</p>
      </div>
    </aside>
  )
}
