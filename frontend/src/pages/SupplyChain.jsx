import { useState } from 'react'
import {
  useSupplyChain, useStockLevels, useReorderAlerts,
  useTransferOrders, useCreateTransfer,
} from '../api/client'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import SeverityBadge from '../components/SeverityBadge'
import {
  Truck, Package, AlertTriangle, ArrowRightLeft, CheckCircle2,
  Clock, XCircle, RefreshCw, ChevronDown, ChevronUp,
  Thermometer, MapPin, BarChart3, Plus, X,
} from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  STOCKOUT:          { label: 'Stockout',   color: 'text-red-300',     bg: 'bg-red-900/30',     bar: '#ef4444' },
  CRITICAL:          { label: 'Critical',   color: 'text-orange-300',  bg: 'bg-orange-900/30',  bar: '#f97316' },
  LOW:               { label: 'Low',        color: 'text-amber-300',   bg: 'bg-amber-900/30',   bar: '#f59e0b' },
  NORMAL:            { label: 'Normal',     color: 'text-emerald-300', bg: 'bg-emerald-900/30', bar: '#34d399' },
  OVERSTOCK:         { label: 'Overstock',  color: 'text-sky-300',     bg: 'bg-sky-900/30',     bar: '#38bdf8' },
}

const TRANSFER_STATUS = {
  PENDING_APPROVAL:  { label: 'Pending',    icon: Clock,         color: 'text-amber-300',   bg: 'bg-amber-900/20' },
  APPROVED:          { label: 'Approved',   icon: CheckCircle2,  color: 'text-brand-300',   bg: 'bg-brand-900/20' },
  IN_TRANSIT:        { label: 'In Transit', icon: Truck,         color: 'text-sky-300',     bg: 'bg-sky-900/20' },
  DELIVERED:         { label: 'Delivered',  icon: CheckCircle2,  color: 'text-emerald-300', bg: 'bg-emerald-900/20' },
  CANCELLED:         { label: 'Cancelled',  icon: XCircle,       color: 'text-slate-400',   bg: 'bg-slate-800/40' },
}

function StatusPill({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.NORMAL
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color} ${cfg.bg}`}>
      {cfg.label}
    </span>
  )
}

function TransferPill({ status }) {
  const cfg = TRANSFER_STATUS[status] ?? TRANSFER_STATUS.PENDING_APPROVAL
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color} ${cfg.bg}`}>
      <Icon size={11} />
      {cfg.label}
    </span>
  )
}

function StockBar({ fill, status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.NORMAL
  const pct = Math.round(Math.min(fill * 100, 100))
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 rounded-full bg-slate-700">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: cfg.bar }}
        />
      </div>
      <span className={`text-xs font-bold tabular-nums w-8 text-right ${cfg.color}`}>{pct}%</span>
    </div>
  )
}

// ── KPI Summary Cards ─────────────────────────────────────────────────────────

function SummaryCards({ data }) {
  const cards = [
    { label: 'Network Fill Rate',    value: `${data.network_fill_rate}%`,           icon: BarChart3,      color: 'text-brand-300' },
    { label: 'Stockout SKUs',        value: data.stockout_skus,                     icon: XCircle,        color: 'text-red-300' },
    { label: 'Critical SKUs',        value: data.critical_skus,                     icon: AlertTriangle,  color: 'text-orange-300' },
    { label: 'Transfers In Transit', value: data.transfers_in_transit,              icon: Truck,          color: 'text-sky-300' },
    { label: 'Pending Approval',     value: data.transfers_pending_approval,         icon: Clock,          color: 'text-amber-300' },
    { label: 'Reorders Pending',     value: data.pending_reorders,                  icon: RefreshCw,      color: 'text-purple-300' },
    { label: 'Auto-Reorders Today',  value: data.auto_reorders_today,               icon: CheckCircle2,   color: 'text-emerald-300' },
    { label: 'Avg Transfer Time',    value: `${data.avg_transfer_time_h}h`,         icon: Clock,          color: 'text-slate-300' },
  ]
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-8 gap-3">
      {cards.map(({ label, value, icon: Icon, color }) => (
        <div key={label} className="card p-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold leading-tight">{label}</span>
            <Icon size={13} className="text-slate-500 shrink-0" />
          </div>
          <p className={`text-xl font-bold tabular-nums ${color}`}>{value}</p>
        </div>
      ))}
    </div>
  )
}

// ── Zone Stock Heatmap ────────────────────────────────────────────────────────

function ZoneHeatmap({ zones }) {
  const [expandedZone, setExpandedZone] = useState(null)

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <MapPin size={15} className="text-brand-400" />
          <span className="font-semibold text-slate-200 text-sm">Network Stock Heatmap</span>
        </div>
        <span className="text-xs text-slate-400">Click zone to expand SKUs</span>
      </div>

      <div className="p-4 space-y-2">
        {zones.map((zone) => {
          const isOpen = expandedZone === zone.zone
          const total = zone.stockout_count + zone.critical_count + zone.low_count + zone.normal_count + zone.overstock_count
          return (
            <div key={zone.zone} className="rounded-xl border border-slate-700/50 overflow-hidden">
              {/* Zone header row */}
              <button
                onClick={() => setExpandedZone(isOpen ? null : zone.zone)}
                className="w-full flex items-center gap-4 px-4 py-3 bg-slate-800/40 hover:bg-slate-700/40 transition-colors text-left"
              >
                <span className="font-semibold text-slate-200 w-32 shrink-0">{zone.zone}</span>
                <span className="text-xs text-slate-400 w-16 shrink-0">{zone.stores} stores</span>

                {/* Status bar breakdown */}
                <div className="flex-1 flex gap-1 h-3 rounded-full overflow-hidden">
                  {zone.stockout_count > 0 && (
                    <div title="Stockout" className="bg-red-500" style={{ width: `${(zone.stockout_count / total) * 100}%` }} />
                  )}
                  {zone.critical_count > 0 && (
                    <div title="Critical" className="bg-orange-500" style={{ width: `${(zone.critical_count / total) * 100}%` }} />
                  )}
                  {zone.low_count > 0 && (
                    <div title="Low" className="bg-amber-500" style={{ width: `${(zone.low_count / total) * 100}%` }} />
                  )}
                  {zone.normal_count > 0 && (
                    <div title="Normal" className="bg-emerald-500" style={{ width: `${(zone.normal_count / total) * 100}%` }} />
                  )}
                  {zone.overstock_count > 0 && (
                    <div title="Overstock" className="bg-sky-500" style={{ width: `${(zone.overstock_count / total) * 100}%` }} />
                  )}
                </div>

                {/* Counts */}
                <div className="flex gap-2 text-xs shrink-0">
                  {zone.stockout_count > 0 && <span className="text-red-300 font-bold">{zone.stockout_count} out</span>}
                  {zone.critical_count > 0 && <span className="text-orange-300 font-bold">{zone.critical_count} crit</span>}
                  {zone.low_count > 0 && <span className="text-amber-300">{zone.low_count} low</span>}
                </div>

                {isOpen ? <ChevronUp size={14} className="text-slate-400 shrink-0" /> : <ChevronDown size={14} className="text-slate-400 shrink-0" />}
              </button>

              {/* Expanded SKU table */}
              {isOpen && (
                <div className="overflow-x-auto border-t border-slate-700/40">
                  <table className="table-base text-xs">
                    <thead>
                      <tr>
                        <th>SKU</th><th>Drug</th><th>Category</th>
                        <th>Qty</th><th>Days of Stock</th><th>Fill Rate</th>
                        <th>Velocity/day</th><th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {zone.skus
                        .sort((a, b) => {
                          const o = { STOCKOUT: 0, CRITICAL: 1, LOW: 2, NORMAL: 3, OVERSTOCK: 4 }
                          return (o[a.status] ?? 5) - (o[b.status] ?? 5)
                        })
                        .map((sku) => (
                          <tr key={sku.sku_id}>
                            <td className="font-mono text-slate-300">{sku.sku_id}</td>
                            <td className="font-medium text-slate-200">{sku.drug_name}</td>
                            <td><span className="text-slate-400">{sku.category}</span></td>
                            <td className="tabular-nums font-semibold">{sku.quantity.toLocaleString()}</td>
                            <td className={`tabular-nums font-bold ${sku.days_of_stock <= 7 ? 'text-red-300' : sku.days_of_stock <= 14 ? 'text-amber-300' : 'text-emerald-300'}`}>
                              {sku.days_of_stock >= 999 ? '—' : `${sku.days_of_stock}d`}
                            </td>
                            <td className="min-w-[130px]"><StockBar fill={sku.fill_rate} status={sku.status} /></td>
                            <td className="tabular-nums text-slate-300">{sku.velocity}</td>
                            <td><StatusPill status={sku.status} /></td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="px-4 pb-3 flex flex-wrap gap-3">
        {Object.entries(STATUS_CONFIG).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: v.bar }} />
            {v.label}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Reorder Alerts Panel ──────────────────────────────────────────────────────

function ReorderAlerts({ alerts, onCreateTransfer }) {
  if (!alerts.length) return (
    <div className="card p-6 text-center text-slate-400 text-sm">
      <CheckCircle2 size={24} className="text-emerald-400 mx-auto mb-2" />
      All stock levels within thresholds
    </div>
  )

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <AlertTriangle size={15} className="text-orange-400" />
          <span className="font-semibold text-slate-200 text-sm">Reorder Alerts</span>
          <span className="text-xs bg-orange-900/30 text-orange-300 px-2 py-0.5 rounded-full font-semibold">{alerts.length}</span>
        </div>
        <span className="text-xs text-slate-400">MERIDIAN · auto-monitored</span>
      </div>

      <div className="overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>Drug</th><th>Zone</th><th>Store</th>
              <th>Stock</th><th>Reorder Pt</th><th>Suggest Qty</th>
              <th>Est. Cost</th><th>Lead</th><th>Priority</th>
              <th>Action</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.alert_id}>
                <td className="font-medium text-slate-200">{a.drug_name}</td>
                <td className="text-xs text-slate-400">{a.zone}</td>
                <td className="font-mono text-xs text-slate-400">{a.store_id}</td>
                <td className={`tabular-nums font-bold ${a.current_stock === 0 ? 'text-red-300' : 'text-orange-300'}`}>
                  {a.current_stock}
                </td>
                <td className="tabular-nums text-slate-400">{a.reorder_point}</td>
                <td className="tabular-nums font-semibold text-brand-300">{a.suggested_order_qty.toLocaleString()}</td>
                <td className="tabular-nums text-slate-300">₹{a.estimated_cost.toLocaleString()}</td>
                <td className="tabular-nums text-slate-400">{a.lead_time_days}d</td>
                <td>
                  <span className={`text-xs font-bold ${a.priority === 'URGENT' ? 'text-red-300' : 'text-slate-400'}`}>
                    {a.priority}
                  </span>
                </td>
                <td>
                  <span className={`text-xs font-semibold ${a.meridian_action === 'AUTO_REORDER' ? 'text-emerald-300' : 'text-amber-300'}`}>
                    {a.meridian_action === 'AUTO_REORDER' ? 'Auto-reorder' : 'Escalate'}
                  </span>
                </td>
                <td>
                  <button
                    onClick={() => onCreateTransfer({
                      sku_id: a.sku_id,
                      drug_name: a.drug_name,
                      destination_store: a.store_id,
                      suggested_qty: a.suggested_order_qty,
                    })}
                    className="text-xs text-brand-400 hover:text-brand-300 font-semibold transition-colors flex items-center gap-1"
                  >
                    <ArrowRightLeft size={12} />
                    Transfer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Transfer Orders Table ─────────────────────────────────────────────────────

function TransferTable({ transfers }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Truck size={15} className="text-brand-400" />
          <span className="font-semibold text-slate-200 text-sm">Transfer Orders</span>
          <span className="text-xs bg-brand-900/30 text-brand-300 px-2 py-0.5 rounded-full font-semibold">{transfers.length}</span>
        </div>
        <span className="text-xs text-slate-400">Network-wide · MERIDIAN managed</span>
      </div>

      <div className="overflow-x-auto">
        <table className="table-base">
          <thead>
            <tr>
              <th>ID</th><th>Drug</th><th>From</th><th>To</th>
              <th>Qty</th><th>By</th><th>Auth</th>
              <th>Cold</th><th>ETA</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {transfers.map((t) => (
              <tr key={t.transfer_id}>
                <td className="font-mono text-xs text-slate-400">{t.transfer_id}</td>
                <td className="font-medium text-slate-200 max-w-[160px] truncate" title={t.drug_name}>{t.drug_name}</td>
                <td className="font-mono text-xs text-slate-400">{t.source_store}</td>
                <td className="font-mono text-xs text-slate-400">{t.destination_store}</td>
                <td className="tabular-nums font-semibold text-slate-200">{t.quantity}</td>
                <td className="text-xs text-brand-300 font-semibold">{t.initiated_by}</td>
                <td>
                  <span className={`text-xs font-semibold ${t.authority_level === 'TIER_1' ? 'text-emerald-300' : 'text-amber-300'}`}>
                    {t.authority_level}
                  </span>
                </td>
                <td className="text-center">
                  {t.cold_chain_required
                    ? <Thermometer size={13} className="text-sky-400 mx-auto" title="Cold chain required" />
                    : <span className="text-slate-600">—</span>}
                </td>
                <td className="tabular-nums text-slate-400 text-xs">
                  {t.eta_hours != null ? `${t.eta_hours}h` : '—'}
                </td>
                <td><TransferPill status={t.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Create Transfer Modal ─────────────────────────────────────────────────────

const _STORE_LIST = [
  'STORE_DEL_001','STORE_DEL_002','STORE_DEL_003','STORE_DEL_004','STORE_DEL_007',
  'STORE_DEL_012','STORE_DEL_018','STORE_DEL_019','STORE_MUM_001','STORE_MUM_002',
  'STORE_MUM_003','STORE_MUM_007','STORE_MUM_008','STORE_BLR_001','STORE_BLR_002',
  'STORE_BLR_006','STORE_BLR_007','STORE_HYD_001','STORE_HYD_004','STORE_CHN_003',
  'STORE_CHN_005',
]

const _SKU_LIST = [
  { sku_id: 'SKU-1001', drug_name: 'Paracetamol 650mg' },
  { sku_id: 'SKU-1002', drug_name: 'ORS Sachets' },
  { sku_id: 'SKU-1003', drug_name: 'Dengue NS1 Test Kit' },
  { sku_id: 'SKU-1004', drug_name: 'Metformin 500mg' },
  { sku_id: 'SKU-1005', drug_name: 'Insulin Glargine' },
  { sku_id: 'SKU-1006', drug_name: 'Amoxicillin 500mg' },
  { sku_id: 'SKU-1007', drug_name: 'Cetirizine 10mg' },
  { sku_id: 'SKU-1008', drug_name: 'Azithromycin 500mg' },
  { sku_id: 'SKU-1009', drug_name: 'Vitamin D3 60K' },
  { sku_id: 'SKU-1010', drug_name: 'Amlodipine 5mg' },
  { sku_id: 'SKU-1011', drug_name: 'Oseltamivir 75mg' },
  { sku_id: 'SKU-1012', drug_name: 'Insulin Regular' },
]

function CreateTransferModal({ prefill, onClose, onSubmit, isPending }) {
  const [form, setForm] = useState({
    sku_id:            prefill?.sku_id ?? 'SKU-1001',
    drug_name:         prefill?.drug_name ?? 'Paracetamol 650mg',
    source_store:      prefill?.source_store ?? 'STORE_DEL_001',
    destination_store: prefill?.destination_store ?? 'STORE_DEL_007',
    quantity:          prefill?.suggested_qty ?? 50,
    reason:            '',
  })

  const handleSkuChange = (e) => {
    const sku = _SKU_LIST.find((s) => s.sku_id === e.target.value)
    setForm((f) => ({ ...f, sku_id: e.target.value, drug_name: sku?.drug_name ?? '' }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (form.source_store === form.destination_store) {
      alert('Source and destination stores cannot be the same.')
      return
    }
    onSubmit({ ...form, quantity: Number(form.quantity) })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/60">
          <div className="flex items-center gap-2">
            <ArrowRightLeft size={18} className="text-brand-400" />
            <span className="font-bold text-slate-100">Create Stock Transfer</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* SKU */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Drug / SKU</label>
            <select
              value={form.sku_id}
              onChange={handleSkuChange}
              className="w-full bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
            >
              {_SKU_LIST.map((s) => (
                <option key={s.sku_id} value={s.sku_id}>{s.drug_name} ({s.sku_id})</option>
              ))}
            </select>
          </div>

          {/* From → To */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">From Store</label>
              <select
                value={form.source_store}
                onChange={(e) => setForm((f) => ({ ...f, source_store: e.target.value }))}
                className="w-full bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              >
                {_STORE_LIST.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">To Store</label>
              <select
                value={form.destination_store}
                onChange={(e) => setForm((f) => ({ ...f, destination_store: e.target.value }))}
                className="w-full bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              >
                {_STORE_LIST.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
              Quantity
              <span className="ml-2 text-slate-500 normal-case font-normal">(≤100 → TIER_1 auto-approve · &gt;100 → TIER_2 requires approval)</span>
            </label>
            <input
              type="number"
              min={1}
              max={9999}
              value={form.quantity}
              onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
              className="w-full bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 tabular-nums"
            />
            <p className={`text-xs mt-1 font-semibold ${form.quantity > 100 ? 'text-amber-300' : 'text-emerald-300'}`}>
              Authority: {form.quantity > 100 ? 'TIER_2 — will require manager approval' : 'TIER_1 — auto-approved'}
            </p>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Reason (optional)</label>
            <textarea
              rows={2}
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
              placeholder="e.g. Expiry risk mitigation, demand surge pre-positioning..."
              className="w-full bg-slate-800 border border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-600 text-slate-300 text-sm font-semibold hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-sm font-semibold transition-colors flex items-center justify-center gap-2"
            >
              {isPending ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRightLeft size={14} />}
              {isPending ? 'Creating…' : 'Create Transfer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SupplyChain() {
  const [showModal, setShowModal]   = useState(false)
  const [prefill,   setPrefill]     = useState(null)
  const [activeTab, setActiveTab]   = useState('transfers')  // 'transfers' | 'reorders'
  const [successMsg, setSuccessMsg] = useState(null)

  const { data: summaryData,   isLoading: s1, isError: e1, refetch: r1 } = useSupplyChain()
  const { data: stockData,     isLoading: s2, isError: e2, refetch: r2 } = useStockLevels()
  const { data: reorderData,   isLoading: s3, isError: e3, refetch: r3 } = useReorderAlerts()
  const { data: transferData,  isLoading: s4, isError: e4, refetch: r4 } = useTransferOrders()
  const createTransfer = useCreateTransfer()

  const isLoading = s1 || s2 || s3 || s4
  const isError   = e1 || e2 || e3 || e4

  if (isLoading) return <PageLoader />
  if (isError)   return <ErrorState message="Supply chain data unavailable" retry={() => { r1(); r2(); r3(); r4() }} />

  const summary   = summaryData ?? {}
  const zones     = stockData?.zones ?? []
  const alerts    = reorderData?.alerts ?? []
  const transfers = transferData?.transfers ?? []

  const openTransferModal = (prefillData = null) => {
    setPrefill(prefillData)
    setShowModal(true)
  }

  const handleCreateTransfer = async (body) => {
    try {
      await createTransfer.mutateAsync(body)
      setShowModal(false)
      setSuccessMsg(`Transfer ${body.drug_name} (${body.quantity} units) created successfully`)
      setTimeout(() => setSuccessMsg(null), 5000)
    } catch (err) {
      alert(`Transfer failed: ${err?.detail ?? err?.message ?? 'Unknown error'}`)
    }
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Supply Chain &amp; Stock</h1>
          <p className="text-sm text-slate-400 mt-0.5">MERIDIAN + NEXUS · Network stock monitoring, transfers &amp; reorder management</p>
        </div>
        <button
          onClick={() => openTransferModal()}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold rounded-xl transition-colors shrink-0"
        >
          <Plus size={15} />
          New Transfer
        </button>
      </div>

      {/* Success banner */}
      {successMsg && (
        <div className="flex items-center gap-3 px-4 py-3 bg-emerald-900/30 border border-emerald-700/50 rounded-xl text-emerald-300 text-sm font-medium">
          <CheckCircle2 size={16} />
          {successMsg}
        </div>
      )}

      {/* KPI cards */}
      <SummaryCards data={summary} />

      {/* Zone heatmap */}
      <ZoneHeatmap zones={zones} />

      {/* Tabs: Transfers | Reorder Alerts */}
      <div>
        <div className="flex gap-1 mb-4 border-b border-slate-700/50">
          {[
            { key: 'transfers', label: 'Transfer Orders',  icon: Truck,         count: transfers.length },
            { key: 'reorders',  label: 'Reorder Alerts',   icon: AlertTriangle, count: alerts.length },
          ].map(({ key, label, icon: Icon, count }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-lg border-b-2 transition-all -mb-px
                ${activeTab === key
                  ? 'border-brand-500 text-brand-300 bg-brand-900/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200'}`}
            >
              <Icon size={14} />
              {label}
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-bold ${activeTab === key ? 'bg-brand-800/50 text-brand-200' : 'bg-slate-700/50 text-slate-400'}`}>
                {count}
              </span>
            </button>
          ))}
        </div>

        {activeTab === 'transfers' && <TransferTable transfers={transfers} />}
        {activeTab === 'reorders' && (
          <ReorderAlerts alerts={alerts} onCreateTransfer={openTransferModal} />
        )}
      </div>

      {/* Create Transfer Modal */}
      {showModal && (
        <CreateTransferModal
          prefill={prefill}
          onClose={() => setShowModal(false)}
          onSubmit={handleCreateTransfer}
          isPending={createTransfer.isPending}
        />
      )}
    </div>
  )
}
