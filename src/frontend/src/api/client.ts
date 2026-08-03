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

function responseContentType(response: Response): string {
  return response.headers?.get?.('content-type')?.toLowerCase() || ''
}

function isJsonContentType(contentType: string): boolean {
  return contentType.includes('application/json') || contentType.includes('+json')
}

async function responsePreview(response: Response): Promise<string> {
  try {
    const text = await response.text()
    return text.replace(/\s+/g, ' ').trim().slice(0, 160)
  } catch {
    return ''
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = apiUrl(path)
  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...authHeaders(),
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    })
  } catch (reason) {
    const message = reason instanceof Error ? reason.message : String(reason)
    throw new Error(`API request failed (${url}): ${message}`)
  }

  const contentType = responseContentType(response)
  const jsonResponse = !contentType || isJsonContentType(contentType)

  if (!response.ok) {
    if (jsonResponse) {
      const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` })) as ApiErrorBody
      throw new Error(body.detail || body.message || `HTTP ${response.status}`)
    }
    const preview = await responsePreview(response)
    throw new Error(
      `API request failed (${url}): HTTP ${response.status}; expected JSON but received ${contentType || 'unknown content type'}${preview ? ` — ${preview}` : ''}`,
    )
  }

  if (response.status === 204) return undefined as T

  if (!jsonResponse) {
    const preview = await responsePreview(response)
    throw new Error(
      `API returned non-JSON content (${url}): ${contentType || 'unknown content type'}${preview ? ` — ${preview}` : ''}`,
    )
  }

  return response.json() as Promise<T>
}
