/**
 * Clinical Decision API client.
 * Connects to the backend v1 clinical_decision endpoints.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = opts
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ClinicalDecisionResponse {
  decision_id: string
  patient_id: string
  recommendation_id: string
  decision_type: string
  reason: string
  evidence_summary: Record<string, any> | null
  confidence: string
  alternatives: Record<string, any>[]
  contraindications: Record<string, any>[]
  created_at: string
  trace_id?: string
}

export interface ClinicalDecisionRequest {
  patient_id: string
  recommendation_id: string
  variants: Record<string, any>[]
  context?: Record<string, any>
}

// ─── API Functions ───────────────────────────────────────────────────────────

export function fetchClinicalDecisionById(id: string): Promise<ClinicalDecisionResponse> {
  return request(`/clinical-decision/${id}`)
}

export function createClinicalDecision(data: ClinicalDecisionRequest): Promise<ClinicalDecisionResponse> {
  return request('/clinical-decision', { method: 'POST', body: data })
}
