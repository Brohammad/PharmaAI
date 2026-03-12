import axios from 'axios'
import { useEffect, useRef, useCallback, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// ── Axios instance ─────────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (r) => r.data,
  (e) => Promise.reject(e?.response?.data ?? e),
)

export default api

// ── Raw fetch functions ────────────────────────────────────────────────────────
export const fetchKPIs          = () => api.get('/dashboard/kpis')
export const fetchEvents        = (limit = 20) => api.get(`/dashboard/events?limit=${limit}`)
export const fetchColdChain     = () => api.get('/cold-chain/overview')
export const fetchCCAlerts      = () => api.get('/cold-chain/alerts')
export const fetchTempTrend     = (unitId) => api.get(`/cold-chain/trend/${unitId}`)
export const fetchEpidemics     = () => api.get('/demand/epidemic-signals')
export const fetchForecast      = (storeId = 'STORE_DEL_001') => api.get(`/demand/forecast?store_id=${storeId}`)
export const fetchForecastChart = () => api.get('/demand/forecast-chart')
export const fetchStaffing      = () => api.get('/staffing/overview')
export const fetchExpiryRisks   = () => api.get('/inventory/expiry-risks')
export const fetchDecisions     = (limit = 15) => api.get(`/decisions/recent?limit=${limit}`)
export const fetchEscalations   = () => api.get('/decisions/escalations')
export const approveEscalation  = (id) => api.post(`/decisions/escalations/${id}/approve`)
export const rejectEscalation   = (id) => api.post(`/decisions/escalations/${id}/reject`)

// ── React Query hooks ──────────────────────────────────────────────────────────
export const useKPIs = () =>
  useQuery({ queryKey: ['kpis'], queryFn: fetchKPIs, refetchInterval: 15_000 })

export const useEvents = (limit = 20) =>
  useQuery({ queryKey: ['events', limit], queryFn: () => fetchEvents(limit), refetchInterval: 6_000 })

export const useColdChain = () =>
  useQuery({ queryKey: ['cold-chain'], queryFn: fetchColdChain, refetchInterval: 20_000 })

export const useCCAlerts = () =>
  useQuery({ queryKey: ['cc-alerts'], queryFn: fetchCCAlerts, refetchInterval: 10_000 })

export const useTempTrend = (unitId) =>
  useQuery({ queryKey: ['temp-trend', unitId], queryFn: () => fetchTempTrend(unitId), enabled: !!unitId })

export const useEpidemics = () =>
  useQuery({ queryKey: ['epidemics'], queryFn: fetchEpidemics, refetchInterval: 30_000 })

export const useForecast = (storeId) =>
  useQuery({ queryKey: ['forecast', storeId], queryFn: () => fetchForecast(storeId), refetchInterval: 60_000 })

export const useForecastChart = () =>
  useQuery({ queryKey: ['forecast-chart'], queryFn: fetchForecastChart, refetchInterval: 60_000 })

export const useStaffing = () =>
  useQuery({ queryKey: ['staffing'], queryFn: fetchStaffing, refetchInterval: 30_000 })

export const useExpiryRisks = () =>
  useQuery({ queryKey: ['expiry-risks'], queryFn: fetchExpiryRisks, refetchInterval: 60_000 })

export const useDecisions = (limit = 15) =>
  useQuery({ queryKey: ['decisions', limit], queryFn: () => fetchDecisions(limit), refetchInterval: 10_000 })

export const useEscalations = () =>
  useQuery({ queryKey: ['escalations'], queryFn: fetchEscalations, refetchInterval: 8_000 })

export const useApproveEscalation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: approveEscalation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['escalations'] }),
  })
}

export const useRejectEscalation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: rejectEscalation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['escalations'] }),
  })
}

// ── WebSocket live-feed hook ───────────────────────────────────────────────────
export function useWebSocket(maxMessages = 60) {
  const [messages, setMessages] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/live`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      clearInterval(reconnectRef.current)
      // Send periodic keep-alive pings
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 25_000)
      ws._ping = ping
    }

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        setMessages((prev) => [data, ...prev].slice(0, maxMessages))
      } catch { /* ignore malformed */ }
    }

    ws.onclose = () => {
      setConnected(false)
      clearInterval(ws._ping)
      // Auto-reconnect every 5s
      reconnectRef.current = setTimeout(connect, 5_000)
    }

    ws.onerror = () => ws.close()
  }, [maxMessages])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { messages, connected }
}
