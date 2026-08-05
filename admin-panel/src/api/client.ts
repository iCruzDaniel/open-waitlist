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
}

// ─── Auth State (localStorage) ──────────────────────────────────────────────

function getStoredToken(): string | null {
  return localStorage.getItem('jwt_token')
}

function storeAuth(token: string) {
  localStorage.setItem('jwt_token', token)
}

function clearAuth() {
  localStorage.removeItem('jwt_token')
}

export function useAuth() {
  const [token, setToken] = useState<string | null>(getStoredToken)

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
    storeAuth(data.access_token)
    api.setAuth(data.access_token)
    setToken(data.access_token)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    api.setAuth(null)
    setToken(null)
  }, [])

  return { token, login, logout, isLoggedIn: !!token }
}

// ─── API Client ─────────────────────────────────────────────────────────────

class ApiClient {
  private token: string | null = null

  setAuth(token: string | null) {
    this.token = token
  }

  private headers(extra?: Record<string, string>): Record<string, string> {
    const h: Record<string, string> = { ...extra }
    if (this.token) h['Authorization'] = `Bearer ${this.token}`
    return h
  }

  authHeaders(): Record<string, string> {
    return this.headers()
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

  async startExport(slug: string): Promise<{ job_id: string }> {
    const res = await fetch(`/waitlists/${slug}/entries/export`, {
      method: 'POST',
      headers: this.authHeaders(),
    })
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Export start failed (${res.status})`)
    }
    return res.json() as Promise<{ job_id: string }>
  }

  async streamExportStatus(
    slug: string,
    jobId: string,
    handlers: {
      onProgress: (progress: number) => void
      onDone: (downloadUrl: string) => void
      onError: (message: string) => void
    }
  ): Promise<void> {
    const res = await fetch(
      `/waitlists/${slug}/entries/export/${jobId}/status`,
      { headers: this.authHeaders() }
    )
    if (res.status === 401) {
      clearAuth()
      window.location.hash = '#/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok || !res.body) {
      throw new Error(`Export status failed (${res.status})`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          let eventType = ''
          let dataLine = ''

          for (const line of frame.split('\n')) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              dataLine = line.slice(5).trim()
            }
          }

          if (!eventType || !dataLine) continue

          const data = JSON.parse(dataLine) as Record<string, unknown>

          switch (eventType) {
            case 'progress':
              handlers.onProgress(data.progress as number)
              break
            case 'done':
              handlers.onDone(data.download_url as string)
              return
            case 'error':
              handlers.onError(data.message as string)
              return
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  async downloadExport(slug: string, jobId: string): Promise<void> {
    const blob = await this.getCsvBlob(
      `/waitlists/${slug}/entries/export/${jobId}/download`
    )
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${slug}-entries.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
}

export const api = new ApiClient()

// Initialize from localStorage on load
api.setAuth(getStoredToken())

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

export async function downloadExport(
  slug: string,
  jobId: string
): Promise<void> {
  return api.downloadExport(slug, jobId)
}

export async function startExport(
  slug: string
): Promise<{ job_id: string }> {
  return api.startExport(slug)
}

export async function streamExportStatus(
  slug: string,
  jobId: string,
  handlers: {
    onProgress: (progress: number) => void
    onDone: (downloadUrl: string) => void
    onError: (message: string) => void
  }
): Promise<void> {
  return api.streamExportStatus(slug, jobId, handlers)
}
