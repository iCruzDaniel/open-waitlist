import { useState, useCallback } from 'react'

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Waitlist {
  id: number
  slug: string
  title: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  entry_count: number
}

export interface Entry {
  id: number
  waitlist_id: number
  data: Record<string, unknown>
  referrer: string | null
  ip_address: string | null
  created_at: string
}

export interface EntriesResponse {
  items: Entry[]
  total: number
  skip: number
  limit: number
}

export interface LoginResponse {
  access_token: string
  token_type: string
  api_key: string
}

// ─── Auth State (localStorage) ──────────────────────────────────────────────

function getStoredToken(): string | null {
  return localStorage.getItem('jwt_token')
}

function getStoredApiKey(): string | null {
  return localStorage.getItem('api_key')
}

function storeAuth(token: string, apiKey: string) {
  localStorage.setItem('jwt_token', token)
  localStorage.setItem('api_key', apiKey)
}

function clearAuth() {
  localStorage.removeItem('jwt_token')
  localStorage.removeItem('api_key')
}

export function useAuth() {
  const [token, setToken] = useState<string | null>(getStoredToken)
  const [apiKey, setApiKey] = useState<string | null>(getStoredApiKey)

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    const data: LoginResponse = await res.json()
    storeAuth(data.access_token, data.api_key)
    api.setAuth(data.access_token, data.api_key)   // ← sync global ApiClient
    setToken(data.access_token)
    setApiKey(data.api_key)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    api.setAuth(null, null)                         // ← clear global ApiClient
    setToken(null)
    setApiKey(null)
  }, [])

  return { token, apiKey, login, logout, isLoggedIn: !!token }
}

// ─── API Client ─────────────────────────────────────────────────────────────

class ApiClient {
  private token: string | null = null
  private apiKey: string | null = null

  setAuth(token: string | null, apiKey: string | null) {
    this.token = token
    this.apiKey = apiKey
  }

  private headers(extra?: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = { ...extra }
    if (this.token) h['Authorization'] = `Bearer ${this.token}`
    if (this.apiKey) h['X-API-Key'] = this.apiKey
    return h
  }

  async get<T>(path: string): Promise<T> {
    const res = await fetch(path, { headers: this.headers() })
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `GET ${path} failed (${res.status})`)
    }
    return res.json()
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(path, {
      method: 'POST',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `POST ${path} failed (${res.status})`)
    }
    return res.json()
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(path, {
      method: 'PUT',
      headers: this.headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `PUT ${path} failed (${res.status})`)
    }
    return res.json()
  }

  async del(path: string): Promise<void> {
    const res = await fetch(path, {
      method: 'DELETE',
      headers: this.headers(),
    })
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok && res.status !== 204) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `DELETE ${path} failed (${res.status})`)
    }
  }

  async getCsvBlob(path: string): Promise<Blob> {
    const res = await fetch(path, { headers: this.headers() })
    if (!res.ok) throw new Error(`CSV download failed (${res.status})`)
    return res.blob()
  }
}

export const api = new ApiClient()

// Initialize from localStorage on load
api.setAuth(getStoredToken(), getStoredApiKey())

// ─── Waitlist API ───────────────────────────────────────────────────────────

export async function fetchWaitlists(): Promise<Waitlist[]> {
  return api.get<Waitlist[]>('/waitlists')
}

export async function createWaitlist(data: {
  slug: string
  title: string
  description?: string
}): Promise<Waitlist> {
  return api.post<Waitlist>('/waitlists', data)
}

export async function updateWaitlist(
  slug: string,
  data: { title?: string; description?: string }
): Promise<Waitlist> {
  return api.put<Waitlist>(`/waitlists/${slug}`, data)
}

export async function deleteWaitlist(slug: string): Promise<void> {
  return api.del(`/waitlists/${slug}`)
}

// ─── Entries API ────────────────────────────────────────────────────────────

export async function fetchEntries(
  slug: string,
  skip = 0,
  limit = 50
): Promise<EntriesResponse> {
  return api.get<EntriesResponse>(
    `/waitlists/${slug}/entries?skip=${skip}&limit=${limit}`
  )
}

export async function downloadCsv(slug: string): Promise<void> {
  const blob = await api.getCsvBlob(`/waitlists/${slug}/entries/csv`)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${slug}-entries.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
