import { create } from 'zustand'
import { api, setToken } from '../lib/api'

interface AuthState {
  user: any | null
  loading: boolean
  error: string | null
  login: (u: string, p: string) => Promise<void>
  register: (u: string, p: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  error: null,
  async login(username, password) {
    set({ error: null })
    try {
      const r = await api.login(username, password)
      setToken(r.token)
      set({ user: r.user, loading: false })
    } catch (e: any) {
      set({ error: e.message, loading: false })
      throw e
    }
  },
  async register(username, password) {
    set({ error: null })
    try {
      await api.register(username, password)
      const r = await api.login(username, password)
      setToken(r.token)
      set({ user: r.user, loading: false })
    } catch (e: any) {
      set({ error: e.message, loading: false })
      throw e
    }
  },
  async logout() {
    try { await api.logout() } catch {}
    setToken(null)
    set({ user: null })
  },
  async refresh() {
    if (!localStorage.getItem('ai-client-token')) {
      set({ user: null, loading: false })
      return
    }
    try {
      const r = await api.me()
      set({ user: r.user, loading: false })
    } catch {
      setToken(null)
      set({ user: null, loading: false })
    }
  }
}))
