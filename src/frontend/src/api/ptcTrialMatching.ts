export interface TrialCriterion {
  name: string
  status: 'match' | 'mismatch' | 'unknown'
  weight: number
  awarded: number
  detail: string
  evidence: unknown
}

export interface TrialMatch {
  nct_id: string
  title: string
  official_title?: string
  status?: string
  phases: string[]
  conditions: string[]
  interventions: Array<Record<string, unknown>>
  target_genes: string[]
  source_url?: string
  score: number
  classification: 'potential_match' | 'insufficient_data' | 'unlikely_match'
  criteria: TrialCriterion[]
  blocking_mismatches: string[]
  missing_or_unparsed: string[]
}

export interface TrialMatchingResponse {
  case_id: string
  selected_gene?: string
  case_facts: {
    genes: string[]
    variants: Array<{ gene: string; protein_change?: string; classification?: string }>
    pathologic_stage?: string
    age_range?: string
    sex?: string
  }
  matches: TrialMatch[]
  summary: {
    total: number
    potential_match: number
    insufficient_data: number
    unlikely_match: number
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export async function getPTCTrialMatches(
  caseId: string,
  gene?: string,
  activeOnly = true,
  limit = 50,
): Promise<TrialMatchingResponse> {
  const params = new URLSearchParams({
    active_only: String(activeOnly),
    limit: String(Math.min(200, Math.max(1, limit))),
  })
  if (gene) params.set('gene', gene)
  const response = await fetch(`/api/v1/ptc-trial-matching/case/${encodeURIComponent(caseId)}?${params.toString()}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}
