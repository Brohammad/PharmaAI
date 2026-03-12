import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import Sidebar from './components/Sidebar'
import { useWebSocket } from './api/client'
import { useAuth } from './api/auth'
import { PageLoader } from './components/LoadingSpinner'

// Lazy-load all pages → each becomes its own chunk
const Dashboard   = lazy(() => import('./pages/Dashboard'))
const ColdChain   = lazy(() => import('./pages/ColdChain'))
const Demand      = lazy(() => import('./pages/Demand'))
const Staffing    = lazy(() => import('./pages/Staffing'))
const Inventory   = lazy(() => import('./pages/Inventory'))
const Decisions   = lazy(() => import('./pages/Decisions'))
const SupplyChain = lazy(() => import('./pages/SupplyChain'))
const Login       = lazy(() => import('./pages/Login'))

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function AppShell() {
  const { connected } = useWebSocket()
  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: '#070d1a' }}
    >
      {/* Persistent mesh gradient wash */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(at 20% 10%, rgba(14,126,246,0.07) 0, transparent 50%), radial-gradient(at 80% 80%, rgba(168,85,247,0.05) 0, transparent 50%)',
        }}
      />
      <Sidebar wsConnected={connected} />
      <main className="flex-1 overflow-y-auto relative">
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/"             element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/cold-chain"   element={<ProtectedRoute><ColdChain /></ProtectedRoute>} />
            <Route path="/demand"       element={<ProtectedRoute><Demand /></ProtectedRoute>} />
            <Route path="/staffing"     element={<ProtectedRoute><Staffing /></ProtectedRoute>} />
            <Route path="/inventory"    element={<ProtectedRoute><Inventory /></ProtectedRoute>} />
            <Route path="/supply-chain" element={<ProtectedRoute><SupplyChain /></ProtectedRoute>} />
            <Route path="/decisions"    element={<ProtectedRoute><Decisions /></ProtectedRoute>} />
            <Route path="/login"        element={<Login />} />
            <Route path="*"           element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}

export default function App() {
  return <AppShell />
}
