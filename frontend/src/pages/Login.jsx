/**
 * PharmaIQ – Login Page  (glassmorphism redesign)
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../api/auth'
import { Brain, Loader2, AlertCircle, Shield, Eye, User, Zap } from 'lucide-react'

const DEMO_ACCOUNTS = [
  {
    username: 'manager@medchain.in',
    password: 'pharmaiq-demo',
    role: 'MANAGER',
    name: 'Ravi Krishnamurthy',
    description: 'Approve / reject escalations',
    icon: Shield,
    accent: '#299cff',
    dimBg: 'rgba(41,156,255,0.08)',
    border: 'rgba(41,156,255,0.2)',
  },
  {
    username: 'admin@medchain.in',
    password: 'pharmaiq-admin',
    role: 'ADMIN',
    name: 'Ananya Singh',
    description: 'Full access including audit log',
    icon: User,
    accent: '#34d399',
    dimBg: 'rgba(52,211,153,0.08)',
    border: 'rgba(52,211,153,0.2)',
  },
  {
    username: 'viewer@medchain.in',
    password: 'pharmaiq-view',
    role: 'VIEWER',
    name: 'Demo Viewer',
    description: 'Read-only across all dashboards',
    icon: Eye,
    accent: '#94a3b8',
    dimBg: 'rgba(148,163,184,0.06)',
    border: 'rgba(148,163,184,0.15)',
  },
]

export default function Login() {
  const { login }   = useAuth()
  const navigate    = useNavigate()
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
    <div
      className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden"
      style={{ background: '#070d1a' }}
    >
      {/* ── Ambient orbs ──────────────────────────────────── */}
      <div
        className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full pointer-events-none animate-float"
        style={{ background: 'radial-gradient(circle, rgba(14,126,246,0.12) 0%, transparent 70%)', filter: 'blur(60px)' }}
      />
      <div
        className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(168,85,247,0.08) 0%, transparent 70%)', filter: 'blur(60px)', animationDelay: '3s' }}
      />

      {/* ── Dot grid ─────────────────────────────────────── */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.15]"
        style={{
          backgroundImage: 'radial-gradient(rgba(255,255,255,0.4) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      {/* ── Card ─────────────────────────────────────────── */}
      <div
        className="relative w-full max-w-[420px] animate-slide-up"
        style={{ filter: 'drop-shadow(0 40px 80px rgba(0,0,0,0.6))' }}
      >
        {/* Top gradient border line */}
        <div
          className="absolute inset-x-8 -top-px h-px rounded-full"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(41,156,255,0.6), rgba(168,85,247,0.4), transparent)' }}
        />

        <div
          className="rounded-3xl p-8"
          style={{
            background: 'rgba(10, 16, 30, 0.8)',
            border: '1px solid rgba(255,255,255,0.07)',
            backdropFilter: 'blur(32px) saturate(200%)',
            WebkitBackdropFilter: 'blur(32px) saturate(200%)',
          }}
        >
          {/* ── Logo block ──────────────────────────────── */}
          <div className="text-center mb-8">
            <div className="relative inline-flex mb-4">
              <div
                className="absolute inset-0 rounded-2xl blur-xl opacity-50 animate-glow-pulse"
                style={{ background: 'linear-gradient(135deg, #299cff, #a855f7)' }}
              />
              <div
                className="relative w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(41,156,255,0.15), rgba(168,85,247,0.1))',
                  border: '1px solid rgba(41,156,255,0.3)',
                  boxShadow: '0 8px 32px rgba(41,156,255,0.2), inset 0 1px 0 rgba(255,255,255,0.1)',
                }}
              >
                <Brain size={26} style={{ color: '#51bdff' }} />
              </div>
            </div>
            <h1 className="text-gradient text-3xl font-bold tracking-tight">PharmaIQ</h1>
            <p className="text-slate-400 text-sm mt-1.5">Autonomous Health Retail Intelligence</p>
            <p className="text-slate-600 text-xs mt-0.5">MedChain India · 320 Pharmacies</p>
          </div>

          {/* ── Sign-in form ─────────────────────────────── */}
          <form onSubmit={handleSubmit} className="space-y-3.5 mb-6">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 tracking-wide">
                Email
              </label>
              <input
                type="email"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="manager@medchain.in"
                required
                className="input-glass"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1.5 tracking-wide">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="input-glass"
              />
            </div>

            {error && (
              <div
                className="flex items-center gap-2 text-xs px-3 py-2 rounded-xl"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#fca5a5' }}
              >
                <AlertCircle size={12} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 text-white font-semibold text-sm py-2.5 rounded-xl transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, #299cff, #0a66e3)',
                boxShadow: '0 4px 20px rgba(41,156,255,0.3)',
              }}
              onMouseEnter={e => !loading && (e.currentTarget.style.boxShadow = '0 6px 28px rgba(41,156,255,0.45)')}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 4px 20px rgba(41,156,255,0.3)')}
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={13} />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          {/* ── Divider ──────────────────────────────────── */}
          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }} />
            </div>
            <div className="relative flex justify-center">
              <span
                className="px-3 text-[11px] font-semibold text-slate-600 tracking-wide uppercase"
                style={{ background: 'rgba(10,16,30,0.8)' }}
              >
                Quick access
              </span>
            </div>
          </div>

          {/* ── Demo cards ───────────────────────────────── */}
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((acc) => {
              const Icon = acc.icon
              return (
                <button
                  key={acc.username}
                  onClick={() => handleDemoLogin(acc)}
                  disabled={loading}
                  className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                  style={{ background: acc.dimBg, border: `1px solid ${acc.border}` }}
                  onMouseEnter={e => { e.currentTarget.style.background = acc.dimBg.replace('0.08', '0.14').replace('0.06', '0.1') }}
                  onMouseLeave={e => { e.currentTarget.style.background = acc.dimBg }}
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: acc.dimBg, border: `1px solid ${acc.border}` }}
                  >
                    <Icon size={13} style={{ color: acc.accent }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[12px] font-semibold text-slate-200">{acc.name}</span>
                      <span
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded-md"
                        style={{ background: acc.dimBg, color: acc.accent, border: `1px solid ${acc.border}` }}
                      >
                        {acc.role}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 truncate">{acc.description}</p>
                  </div>
                  <span className="text-[10px] font-medium shrink-0" style={{ color: acc.accent, opacity: 0.6 }}>
                    1-click →
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Bottom tag */}
        <p className="text-center text-[11px] text-slate-700 mt-4">
          PharmaIQ v2.0 · LangGraph + Gemini 1.5 Flash
        </p>
      </div>
    </div>
  )
}
