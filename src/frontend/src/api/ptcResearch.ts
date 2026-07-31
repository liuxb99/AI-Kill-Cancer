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

export interface PTCTherapy {
  therapy_key: string
  name: string
  generic_name?: string
  therapy_type: string
  approval_status?: string
  indications: string[]
  mechanism?: string
  warnings: string[]
  source_name: string
  source_record_id: string
  source_url?: string
}

export interface PTCTrial {
  nct_id: string
  brief_title: string
  overall_status?: string
  phases: string[]
  conditions: string[]
  interventions: Array<{ name?: string; type?: string; description?: string }>
  enrollment?: number
  locations: Array<{ facility?: string; city?: string; state?: string; country?: string }>
  source_url?: string
}

export interface PTCEvidence {
  evidence_key: string
  source_name: string
  title?: string
  summary?: string
  evidence_type: string
  evidence_level?: string
  direction?: string
  gene_symbol?: string
  variant?: string
  citation?: string
  source_url?: string
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

export function listPTCTherapies(gene?: string): Promise<PTCTherapy[]> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  return request(`/ptc-knowledge/therapies${params.toString() ? `?${params}` : ''}`)
}

export function listPTCTrials(recruitingOnly = false): Promise<PTCTrial[]> {
  return request(`/ptc-knowledge/trials?recruiting_only=${recruitingOnly}`)
}

export function listPTCEvidence(gene?: string): Promise<PTCEvidence[]> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  return request(`/ptc-knowledge/evidence${params.toString() ? `?${params}` : ''}`)
}

export function getPTCGeneKnowledge(gene: string): Promise<{
  gene: string
  therapies: PTCTherapy[]
  trials: PTCTrial[]
  evidence: PTCEvidence[]
}> {
  return request(`/ptc-knowledge/gene/${encodeURIComponent(gene)}`)
}

export function syncPTCClinicalTrials(pageSize = 100) {
  return request<{ status: string; records: number }>(`/ptc-knowledge/sync/clinical-trials?page_size=${pageSize}`, { method: 'POST' })
}

export function syncPTCOpenFDA(drugNames: string[]) {
  return request<{ status: string; records: number }>('/ptc-knowledge/sync/openfda', {
    method: 'POST',
    body: JSON.stringify({ drug_names: drugNames }),
  })
}
