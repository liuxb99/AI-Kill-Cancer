export interface PTCEvidenceMatrixRow {
  gene: string
  variants: Array<{ variant_id: string; protein_change?: string; classification?: string }>
  protein_domain?: string
  pathway?: string
  score: number
  score_components: Record<string, number>
  therapies: Array<{
    therapy_key: string
    name: string
    approval_status?: string
    mechanism?: string
    source?: string
    url?: string
  }>
  evidence: Array<{
    evidence_key: string
    title?: string
    source?: string
    level?: string
    direction?: string
    publication_id?: string
    url?: string
    figures: number
    tables: number
  }>
  trials: Array<{
    nct_id: string
    title?: string
    status?: string
    phases?: string[]
    active: boolean
    url?: string
  }>
  cohort: {
    same_gene_cases: number
    vital_status_distribution: Record<string, number>
    outcome_distribution: Record<string, number>
  }
  assets: { figures: number; tables: number }
  gaps: string[]
}

export interface PTCEvidenceMatrixResponse {
  case_id: string
  source_dataset: string
  pathologic_stage?: string
  rows: PTCEvidenceMatrixRow[]
  summary: {
    genes: number
    therapies: number
    evidence: number
    trials: number
    open_full_text_assets: number
    unresolved_gaps: number
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export async function getPTCEvidenceMatrix(caseId: string, gene?: string): Promise<PTCEvidenceMatrixResponse> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  const suffix = params.toString() ? `?${params}` : ''
  const path = `/api/v1/ptc-evidence-matrix/case/${encodeURIComponent(caseId)}${suffix}`
  const response = await fetch(path)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `Unable to load evidence matrix from ${path}`)
  }
  return response.json()
}
