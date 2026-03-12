import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Thermometer, TrendingUp, Users,
  Package, Brain, Activity, ChevronRight, Zap, Truck,
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
    <aside className="w-64 shrink-0 flex flex-col bg-slate-900/80 border-r border-slate-700/50 h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-600/30">
            <Activity size={18} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-base leading-none tracking-tight">PharmaIQ</p>
            <p className="text-slate-400 text-xs mt-0.5">MedChain India</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map(({ to, icon: Icon, label, sub }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all group
               ${isActive
                 ? 'bg-brand-600/20 text-brand-300 border border-brand-600/30'
                 : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700/40 border border-transparent'}`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={17} className={isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'} />
                <span className="flex-1">
                  <span className="block font-medium leading-none">{label}</span>
                  <span className="block text-xs text-slate-500 mt-0.5">{sub}</span>
                </span>
                {isActive && <ChevronRight size={14} className="text-brand-400" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer — WS status */}
      <div className="px-5 py-4 border-t border-slate-700/50">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
          <span className="text-xs text-slate-400">
            {wsConnected ? 'Live feed active' : 'Reconnecting…'}
          </span>
          <Zap size={12} className={wsConnected ? 'text-emerald-400 ml-auto' : 'text-slate-600 ml-auto'} />
        </div>
        <p className="text-xs text-slate-600 mt-2">8 Agents · 320 Pharmacies</p>
      </div>
    </aside>
  )
}
