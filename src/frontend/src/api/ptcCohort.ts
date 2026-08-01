import { apiRequest, withQuery } from './client'

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
    variants: Array<{ variant_id: string; gene: string; protein_change?: string; classification?: string }>
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
  methodology: {
    scoring_version: string
    outcome_blind: boolean
    outcome_fields_excluded: string[]
    outcome_usage: 'post_match_descriptive_summary_only'
    candidate_window: number
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
    outcomes_used_for_ranking: boolean
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export function getPTCSimilarCases(caseId: string, limit = 20, minScore = 0): Promise<PTCCohortResponse> {
  return apiRequest(withQuery(`/ptc-cohort/case/${encodeURIComponent(caseId)}/similar`, {
    limit,
    min_score: minScore,
  }))
}
