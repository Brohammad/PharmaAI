import { useState } from 'react'
import { useDecisions, useEscalations, useApproveEscalation, useRejectEscalation } from '../api/client'
import { useAuth } from '../api/auth'
import AgentBadge from '../components/AgentBadge'
import SeverityBadge from '../components/SeverityBadge'
import { PageLoader, ErrorState } from '../components/LoadingSpinner'
import { Brain, CheckCircle2, XCircle, Clock, Shield, AlertTriangle, Lock } from 'lucide-react'

const AUTHORITY_COLORS = {
  TIER_1: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  TIER_2: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  TIER_3: 'bg-red-500/10 text-red-300 border-red-500/20',
  HUMAN_REQUIRED: 'bg-purple-500/10 text-purple-300 border-purple-500/20',
}

function AuthorityBadge({ level }) {
  const cls = AUTHORITY_COLORS[level] ?? 'bg-slate-600/20 text-slate-400 border-slate-600/30'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      <Shield size={10} />
      {level?.replace('_', ' ')}
    </span>
  )
}

function EscalationCard({ item, onApprove, onReject, approving, rejecting, canAct, actionError }) {
  return (
    <div className="card p-5 border-l-4 border-l-purple-500 space-y-3 animate-slide-up">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-bold text-slate-100">{item.action_type}</span>
            <AuthorityBadge level="HUMAN_REQUIRED" />
          </div>
          <p className="text-sm text-slate-400">{item.reason_for_escalation}</p>
        </div>
        <SeverityBadge label={item.status ?? 'PENDING'} />
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="rounded-lg bg-slate-800/60 p-2">
          <p className="text-slate-500">Store</p>
          <p className="font-semibold text-slate-200 mt-0.5 truncate">{item.store_id}</p>
        </div>
        <div className="rounded-lg bg-slate-800/60 p-2">
          <p className="text-slate-500">Financial Impact</p>
          <p className="font-bold text-amber-300 mt-0.5">₹{(item.financial_impact ?? 0).toLocaleString()}</p>
        </div>
        <div className="rounded-lg bg-slate-800/60 p-2">
          <p className="text-slate-500">Expires</p>
          <p className="font-semibold text-red-300 mt-0.5">{item.expires_in ?? '4h'}</p>
        </div>
      </div>

      {item.nexus_recommendation && (
        <div className="rounded-lg bg-slate-800/40 border border-slate-700/40 p-3">
          <p className="text-xs text-slate-500 mb-1">NEXUS Recommendation</p>
          <p className="text-sm text-slate-300">{item.nexus_recommendation}</p>
        </div>
      )}

      {/* Error feedback */}
      {actionError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#e2a0a0' }}>
          <AlertTriangle size={12} />
          {actionError}
        </div>
      )}

      {item.status === 'PENDING_HUMAN_APPROVAL' && (
        canAct ? (
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => onApprove(item.escalation_id)}
              disabled={approving || rejecting}
              className="btn-success flex-1 justify-center"
            >
              <CheckCircle2 size={14} />
              {approving ? 'Approving…' : 'Approve'}
            </button>
            <button
              onClick={() => onReject(item.escalation_id)}
              disabled={approving || rejecting}
              className="btn-danger flex-1 justify-center"
            >
              <XCircle size={14} />
              {rejecting ? 'Rejecting…' : 'Reject'}
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
            style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', color: '#a893cc' }}>
            <Lock size={12} />
            Requires MANAGER or ADMIN role to approve / reject
          </div>
        )
      )}
    </div>
  )
}

export default function Decisions() {
  const { user } = useAuth()
  const { data: decisionsData, isLoading: dLoading, isError: dError } = useDecisions(20)
  const { data: escalationsData, isLoading: eLoading } = useEscalations()
  const [actionError, setActionError] = useState(null)

  const { mutate: approve, isPending: approving } = useApproveEscalation()
  const { mutate: reject,  isPending: rejecting  } = useRejectEscalation()

  if (dLoading) return <PageLoader />
  if (dError) return <ErrorState message="Decisions data unavailable" />

  const decisions   = decisionsData?.decisions ?? []
  const escalations = escalationsData?.escalations ?? []
  const pending     = escalations.filter((e) => e.status === 'PENDING_HUMAN_APPROVAL')

  const ROLE_RANK = { VIEWER: 0, PHARMACIST: 1, MANAGER: 2, ADMIN: 3 }
  const canAct = ROLE_RANK[user?.role] >= ROLE_RANK['MANAGER']

  function handleApprove(id) {
    setActionError(null)
    approve(id, {
      onError: (err) => setActionError(err?.detail || err?.message || 'Approval failed. Check your permissions.'),
    })
  }

  function handleReject(id) {
    setActionError(null)
    reject(id, {
      onError: (err) => setActionError(err?.detail || err?.message || 'Rejection failed. Check your permissions.'),
    })
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Decisions & Audit</h1>
          <p className="text-sm text-slate-400 mt-0.5">NEXUS · CRITIQUE · COMPLIANCE — Authority matrix enforcement</p>
        </div>
        {pending.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 animate-pulse-slow">
            <AlertTriangle size={13} className="text-purple-400" />
            <span className="text-xs font-semibold text-purple-300">{pending.length} pending approval</span>
          </div>
        )}
      </div>

      {/* Escalation queue — top priority */}
      {escalations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Clock size={15} className="text-purple-400" />
            <h2 className="font-semibold text-slate-200 text-sm">Escalation Queue</h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {eLoading && <div className="text-slate-500 text-sm p-4">Loading escalations…</div>}
            {escalations.map((item) => (
              <EscalationCard
                key={item.escalation_id}
                item={item}
                onApprove={handleApprove}
                onReject={handleReject}
                approving={approving}
                rejecting={rejecting}
                canAct={canAct}
                actionError={actionError}
              />
            ))}
          </div>
        </div>
      )}

      {/* Decision log table */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Brain size={15} className="text-brand-400" />
            <span className="font-semibold text-slate-200 text-sm">NEXUS Decision Log</span>
          </div>
          <span className="text-xs text-slate-400">{decisions.length} recent decisions</span>
        </div>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Store</th>
                <th>Authority</th>
                <th>CRITIQUE</th>
                <th>COMPLIANCE</th>
                <th>NEXUS Verdict</th>
                <th>Source Agent</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((d, i) => (
                <tr key={i}>
                  <td className="text-xs text-slate-500 tabular-nums whitespace-nowrap">{d.timestamp ? new Date(d.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                  <td>
                    <span className="font-medium text-slate-200 text-xs">{d.action_type}</span>
                  </td>
                  <td className="text-xs font-mono text-slate-400">{d.store_id}</td>
                  <td><AuthorityBadge level={d.authority_level} /></td>
                  <td><SeverityBadge label={d.critique_verdict ?? '—'} showDot={false} /></td>
                  <td><SeverityBadge label={d.compliance_verdict ?? '—'} showDot={false} /></td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      {d.nexus_verdict === 'APPROVED' || d.nexus_verdict === 'APPROVED_WITH_CONDITIONS'
                        ? <CheckCircle2 size={13} className="text-emerald-400" />
                        : d.nexus_verdict === 'ESCALATED'
                        ? <Clock size={13} className="text-purple-400" />
                        : <XCircle size={13} className="text-red-400" />
                      }
                      <SeverityBadge label={d.nexus_verdict ?? '—'} showDot={false} />
                    </div>
                  </td>
                  <td><AgentBadge agent={d.source_agent} size="xs" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
