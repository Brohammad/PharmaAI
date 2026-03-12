import { useExpiryRisks } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { Package, Clock, AlertTriangle, TrendingDown } from 'lucide-react'

function RiskBar({ value }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#34d399'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-700">
        <div className="h-1.5 rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-xs font-bold tabular-nums" style={{ color }}>{pct}%</span>
    </div>
  )
}

function DaysLeft({ days }) {
  const color = days <= 7 ? 'text-red-300' : days <= 30 ? 'text-amber-300' : 'text-emerald-300'
  return <span className={`font-bold tabular-nums text-sm ${color}`}>{days}d</span>
}

export default function Inventory() {
  const { data, isLoading, isError, refetch } = useExpiryRisks()

  if (isLoading) return <PageLoader />
  if (isError) return <ErrorState message="Inventory data unavailable" retry={refetch} />

  const items = data?.items ?? []
  const critical = items.filter((i) => i.days_until_expiry <= 7).length
  const warning  = items.filter((i) => i.days_until_expiry > 7 && i.days_until_expiry <= 30).length
  const totalValue = items.reduce((acc, i) => acc + (i.estimated_loss_value ?? 0), 0)

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Inventory & Expiry Risk</h1>
        <p className="text-sm text-slate-400 mt-0.5">MERIDIAN Agent · Near-expiry SKU management</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Risk Items', value: items.length, icon: Package, color: 'text-brand-300' },
          { label: 'Critical (≤7 days)', value: critical, icon: AlertTriangle, color: 'text-red-300' },
          { label: 'Warning (≤30 days)', value: warning, icon: Clock, color: 'text-amber-300' },
          { label: 'Est. Loss Value', value: `₹${totalValue.toLocaleString()}`, icon: TrendingDown, color: 'text-orange-300' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{label}</span>
              <Icon size={15} className="text-slate-500" />
            </div>
            <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Expiry table */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Package size={15} className="text-brand-400" />
            <span className="font-semibold text-slate-200 text-sm">Near-Expiry SKUs</span>
          </div>
          <span className="text-xs text-slate-400 font-medium">{items.length} items</span>
        </div>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr>
                <th>SKU</th><th>Drug Name</th><th>Store</th>
                <th>Qty</th><th>Days Left</th><th>Risk Score</th>
                <th>Est. Loss</th><th>Intervention</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.sort((a, b) => a.days_until_expiry - b.days_until_expiry).map((item, i) => (
                <tr key={i}>
                  <td className="font-mono text-xs text-slate-300">{item.sku_id}</td>
                  <td className="font-medium text-slate-200">{item.drug_name}</td>
                  <td className="text-xs font-mono text-slate-400">{item.store_id}</td>
                  <td className="tabular-nums">{item.quantity?.toLocaleString()}</td>
                  <td><DaysLeft days={item.days_until_expiry} /></td>
                  <td className="min-w-[120px]"><RiskBar value={item.risk_score ?? 0.5} /></td>
                  <td className="tabular-nums text-orange-300 font-semibold">₹{(item.estimated_loss_value ?? 0).toLocaleString()}</td>
                  <td className="text-xs text-slate-400">{item.recommended_intervention ?? 'Monitor'}</td>
                  <td><SeverityBadge label={item.days_until_expiry <= 7 ? 'CRITICAL' : item.days_until_expiry <= 30 ? 'HIGH' : 'MEDIUM'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
