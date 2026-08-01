export interface ApiErrorBody {
  detail?: string
  message?: string
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return normalized.startsWith('/api/') ? normalized : `/api/v1${normalized}`
}

export function withQuery(path: string, params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  })
  const suffix = search.toString()
  return suffix ? `${path}${path.includes('?') ? '&' : '?'}${suffix}` : path
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const hasBody = options.body !== undefined && options.body !== null
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      ...authHeaders(),
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as ApiErrorBody
    throw new Error(body.detail || body.message || `HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
