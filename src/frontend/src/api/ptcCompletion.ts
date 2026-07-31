const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export interface PTCSourceStatus {
  cases: number
  variants: number
  outcomes: number
  therapies: number
  evidence: number
  clinical_trials: number
  herbs: number
  compounds: number
  interactions: number
  knowledge_sources: Record<string, number>
}

export interface PTCSyncStage {
  status: 'success' | 'failed' | 'skipped'
  result?: unknown
  error?: string
  reason?: string
}

export interface PTCSyncResult {
  status: 'completed' | 'completed_with_errors'
  started_at: string
  finished_at: string
  duration_seconds: number
  stages: Record<string, PTCSyncStage>
  summary: PTCSourceStatus
}

export interface PTCOutcomeByGene {
  gene: string
  case_count: number
  vital_status: Record<string, number>
  outcomes: Record<string, number>
}

export interface PTCCompleteGraph {
  generated_at: string
  node_count: number
  edge_count: number
  nodes: Array<{ id: string; type: string; label: string; properties: Record<string, unknown> }>
  edges: Array<{ id: string; source: string; target: string; relation: string; properties: Record<string, unknown> }>
}

export function getPTCSourceStatus(): Promise<PTCSourceStatus> {
  return request('/ptc-completion/status')
}

export function getPTCOutcomesByGene(): Promise<PTCOutcomeByGene[]> {
  return request('/ptc-completion/outcomes/by-gene')
}

export function getPTCCompleteGraph(caseLimit = 500): Promise<PTCCompleteGraph> {
  return request(`/ptc-completion/graph?case_limit=${caseLimit}`)
}

export function syncPTCCompletePipeline(payload: {
  gdc_size: number
  trial_size: number
  pubmed_size: number
  drug_names: string[]
  include_civic: boolean
}): Promise<PTCSyncResult> {
  return request('/ptc-completion/sync-all', { method: 'POST', body: JSON.stringify(payload) })
}
