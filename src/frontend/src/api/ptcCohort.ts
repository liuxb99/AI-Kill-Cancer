const API_BASE = import.meta.env.VITE_API_URL || ''

export interface PTCCohortMatch {
  case_id: string
  source_dataset: string
  score: number
  components: Record<string, number>
  shared_genes: string[]
  shared_protein_variants: string[]
  case_facts: {
    pathologic_stage?: string
    tnm: Array<string | null>
    age_range?: string
    sex?: string
    vital_status?: string
    days_to_last_follow_up?: number
    days_to_death?: number
    genes: string[]
    variants: Array<{
      variant_id: string
      gene: string
      protein_change?: string
      classification?: string
    }>
    outcomes: Array<{ type: string; value?: string }>
  }
}

export interface PTCCohortResponse {
  anchor: {
    case_id: string
    source_dataset: string
    pathologic_stage?: string
    tnm: Array<string | null>
    genes: string[]
    protein_variants: string[]
  }
  weights: Record<string, number>
  matches: PTCCohortMatch[]
  cohort: {
    size: number
    stage_distribution: Record<string, number>
    vital_status_distribution: Record<string, number>
    top_genes: Array<{ gene: string; cases: number }>
    outcome_distribution: Record<string, number>
    mean_follow_up_days?: number
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export async function getPTCSimilarCases(
  caseId: string,
  limit = 20,
  minScore = 0,
): Promise<PTCCohortResponse> {
  const params = new URLSearchParams({ limit: String(limit), min_score: String(minScore) })
  const response = await fetch(
    `${API_BASE}/api/v1/ptc-cohort/case/${encodeURIComponent(caseId)}/similar?${params.toString()}`,
  )
  if (!response.ok) throw new Error(`无法载入相似病例队列：HTTP ${response.status}`)
  return response.json()
}
