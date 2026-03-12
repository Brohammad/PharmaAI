/**
 * PharmaIQ – Login Page
 * Full-screen login with role selection for demos.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../api/auth'
import { Brain, Loader2, AlertCircle, Shield, Eye, User } from 'lucide-react'

const DEMO_ACCOUNTS = [
  {
    username: 'manager@medchain.in',
    password: 'pharmaiq-demo',
    role: 'MANAGER',
    name: 'Ravi Krishnamurthy',
    description: 'Can approve / reject escalations',
    icon: Shield,
    color: 'text-brand-400',
    bg: 'bg-brand-500/10 border-brand-500/30',
  },
  {
    username: 'admin@medchain.in',
    password: 'pharmaiq-admin',
    role: 'ADMIN',
    name: 'Ananya Singh',
    description: 'Full access including audit log',
    icon: User,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-500/30',
  },
  {
    username: 'viewer@medchain.in',
    password: 'pharmaiq-view',
    role: 'VIEWER',
    name: 'Demo Viewer',
    description: 'Read-only access to all dashboards',
    icon: Eye,
    color: 'text-slate-400',
    bg: 'bg-slate-500/10 border-slate-500/30',
  },
]

export default function Login() {
  const { login }       = useAuth()
  const navigate        = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(err?.detail || 'Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDemoLogin(account) {
    setError(null)
    setLoading(true)
    try {
      await login(account.username, account.password)
      navigate('/')
    } catch (err) {
      setError(err?.detail || 'Demo login failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] opacity-20" />

      <div className="relative w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-500/15 border border-brand-500/30 mb-4">
            <Brain size={28} className="text-brand-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">PharmaIQ</h1>
          <p className="text-slate-400 text-sm mt-1">
            Autonomous Health Retail Intelligence
          </p>
          <p className="text-slate-500 text-xs mt-0.5">
            MedChain India · 320 Pharmacies
          </p>
        </div>

        {/* Login card */}
        <div className="bg-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-4 mb-6">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="manager@medchain.in"
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle size={13} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-sm py-2.5 rounded-xl transition"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : null}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative mb-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-slate-900 px-3 text-xs text-slate-500">Demo accounts</span>
            </div>
          </div>

          {/* Demo quick-login cards */}
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((acc) => {
              const Icon = acc.icon
              return (
                <button
                  key={acc.username}
                  onClick={() => handleDemoLogin(acc)}
                  disabled={loading}
                  className={`w-full flex items-center gap-3 p-3 rounded-xl border ${acc.bg} hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition text-left`}
                >
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${acc.bg}`}>
                    <Icon size={14} className={acc.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-200">{acc.name}</span>
                      <span className={`text-[10px] font-bold ${acc.color}`}>{acc.role}</span>
                    </div>
                    <p className="text-[11px] text-slate-500 truncate">{acc.description}</p>
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">click to login</span>
                </button>
              )
            })}
          </div>
        </div>

        <p className="text-center text-xs text-slate-600 mt-4">
          PharmaIQ v2.0 · Powered by LangGraph + Gemini
        </p>
      </div>
    </div>
  )
}
