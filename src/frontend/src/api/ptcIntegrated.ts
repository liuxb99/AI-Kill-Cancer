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

export interface PTCDashboard {
  case_count: number
  variant_count: number
  therapy_count: number
  evidence_count: number
  trial_count: number
  herb_count: number
  interaction_count: number
  top_genes: Array<{ gene: string; case_count: number }>
}

export interface PTCHerb {
  herb_key: string
  chinese_name: string
  english_name?: string
  latin_name?: string
  medicinal_part?: string
  traditional_functions: string[]
  investigated_genes: string[]
  investigated_pathways: string[]
  evidence_level: string
  evidence_summary?: string
  source_name: string
  source_record_id?: string
}

export interface PTCInteraction {
  herb_key: string
  therapy_key: string
  interaction_type: string
  severity: string
  mechanism?: string
  clinical_effect?: string
  recommendation?: string
  evidence_level: string
  source_name: string
}

export interface PTCIntegratedRecommendation {
  recommendation_id: string
  case_id: string
  genes: string[]
  ranked_therapies: Array<Record<string, any>>
  matching_trials: Array<Record<string, any>>
  supporting_evidence: Array<Record<string, any>>
  herb_research: Array<Record<string, any>>
  interaction_warnings: Array<Record<string, any>>
  similar_cases: Array<Record<string, any>>
  explanation: string
  confidence: number
  engine_version: string
  generated_at: string
}

export function getPTCIntegratedDashboard(): Promise<PTCDashboard> {
  return request('/ptc-integrated/dashboard')
}

export function bootstrapPTCHerbs(): Promise<{ herbs_created: number; compounds_created: number }> {
  return request('/ptc-integrated/bootstrap/herbs', { method: 'POST' })
}

export function listPTCHerbs(gene?: string): Promise<PTCHerb[]> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  const suffix = params.toString() ? `?${params}` : ''
  return request(`/ptc-integrated/herbs${suffix}`)
}

export function listPTCInteractions(): Promise<PTCInteraction[]> {
  return request('/ptc-integrated/interactions')
}

export function calculatePTCSimilarity(caseId: string) {
  return request<Array<Record<string, any>>>(`/ptc-integrated/cases/${encodeURIComponent(caseId)}/similarity`, { method: 'POST' })
}

export function generatePTCIntegratedRecommendation(caseId: string): Promise<PTCIntegratedRecommendation> {
  return request(`/ptc-integrated/cases/${encodeURIComponent(caseId)}/recommendation`, { method: 'POST' })
}
