import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import Sidebar from './components/Sidebar'
import { useWebSocket } from './api/client'
import { PageLoader } from './components/LoadingSpinner'

// Lazy-load all pages → each becomes its own chunk
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ColdChain = lazy(() => import('./pages/ColdChain'))
const Demand    = lazy(() => import('./pages/Demand'))
const Staffing  = lazy(() => import('./pages/Staffing'))
const Inventory = lazy(() => import('./pages/Inventory'))
const Decisions = lazy(() => import('./pages/Decisions'))

export default function App() {
  const { connected } = useWebSocket()

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      <Sidebar wsConnected={connected} />

      <main className="flex-1 overflow-y-auto">
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/cold-chain" element={<ColdChain />} />
            <Route path="/demand"     element={<Demand />} />
            <Route path="/staffing"   element={<Staffing />} />
            <Route path="/inventory"  element={<Inventory />} />
            <Route path="/decisions"  element={<Decisions />} />
            <Route path="*"           element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
