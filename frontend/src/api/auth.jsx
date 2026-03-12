/**
 * PharmaIQ – Auth Context
 * Stores JWT token in localStorage, provides login/logout helpers,
 * injects Authorization header into all axios requests.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import api from './client'

// Separate axios instance for auth endpoints (base /)
const authApi = axios.create({ baseURL: '/' })

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]   = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('pharmaiq_token'))

  // Inject/remove Authorization header when token changes
  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      authApi.defaults.headers.common['Authorization'] = `Bearer ${token}`
      // Check expiry
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        if (payload.exp * 1000 <= Date.now()) logout()
      } catch { logout() }
    } else {
      delete api.defaults.headers.common['Authorization']
      delete authApi.defaults.headers.common['Authorization']
    }
  }, [token])

  const login = useCallback(async (username, password) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    // POST as form-encoded (OAuth2 spec)
    const { data } = await authApi.post('auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    localStorage.setItem('pharmaiq_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('pharmaiq_token')
    setToken(null)
    setUser(null)
    delete api.defaults.headers.common['Authorization']
  }, [])

  // On mount, restore user from token if still valid
  useEffect(() => {
    if (token && !user) {
      authApi.get('auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(r => setUser(r.data))
        .catch(logout)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
