const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export interface PTCVariant {
  variant_id?: string
  gene: string
  chromosome?: string
  position?: number
  reference?: string
  alternate?: string
  variant_type?: string
  classification?: string
  protein_change?: string
  source_record_id?: string
}

export interface PTCOutcome {
  outcome_id?: string
  outcome_type: string
  outcome_value?: string
  observed_at?: string
  source_record_id?: string
}

export interface PTCResearchCase {
  case_id: string
  source_dataset: string
  source_project: string
  disease: string
  sex?: string
  age_range?: string
  pathologic_stage?: string
  t_status?: string
  n_status?: string
  m_status?: string
  vital_status?: string
  days_to_last_follow_up?: number
  days_to_death?: number
  variants: PTCVariant[]
  outcomes: PTCOutcome[]
}

export interface PTCGraphPath {
  case_id: string
  nodes: Array<{ id: string; type: string; label: string }>
  edges: Array<{ id: string; source: string; target: string; relation: string }>
}

export function listPTCCases(gene?: string): Promise<PTCResearchCase[]> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  const suffix = params.toString() ? `?${params}` : ''
  return request(`/ptc-research/cases${suffix}`)
}

export function getPTCCase(caseId: string): Promise<PTCResearchCase> {
  return request(`/ptc-research/cases/${encodeURIComponent(caseId)}`)
}

export function getPTCGraphPath(caseId: string): Promise<PTCGraphPath> {
  return request(`/ptc-research/cases/${encodeURIComponent(caseId)}/graph-path`)
}

export function importPTCRecords(records: unknown[], sourceVersion?: string) {
  return request<{
    batch_id: string
    imported_cases: number
    imported_variants: number
    imported_outcomes: number
    outbox_events: number
  }>('/ptc-research/imports', {
    method: 'POST',
    body: JSON.stringify({ records, source_version: sourceVersion }),
  })
}
