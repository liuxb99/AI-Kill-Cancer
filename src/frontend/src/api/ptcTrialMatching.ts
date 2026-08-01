import { apiRequest, withQuery } from './client'

export interface TrialCriterion {
  name: string
  track: 'relevance' | 'eligibility'
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
  locations: Array<Record<string, unknown>>
  source_url?: string
  score: number
  score_type: 'research_relevance'
  score_version: string
  classification: 'research_candidate' | 'insufficient_relevance_data' | 'low_relevance'
  eligibility_status: 'conflict_detected' | 'incomplete_review_required' | 'criteria_text_aligned_review_required'
  eligibility_determination: false
  relevance_criteria: TrialCriterion[]
  eligibility_criteria: TrialCriterion[]
  criteria: TrialCriterion[]
  blocking_relevance_mismatches: string[]
  eligibility_conflicts: string[]
  missing_or_unverified_eligibility: string[]
  missing_relevance_metadata: string[]
}

export interface TrialMatchingResponse {
  case_id: string
  selected_gene?: string
  methodology: {
    matching_version: string
    score_type: 'research_relevance'
    maximum_score: number
    eligibility_separate_from_score: true
    eligibility_determination: false
    eligibility_fields: string[]
    required_for_real_eligibility: string[]
  }
  weights: Record<string, number>
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
    research_candidate: number
    insufficient_relevance_data: number
    low_relevance: number
    eligibility_conflict_detected: number
    eligibility_review_required: number
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export function getPTCTrialMatches(
  caseId: string,
  gene?: string,
  activeOnly = true,
  limit = 50,
): Promise<TrialMatchingResponse> {
  return apiRequest(withQuery(`/ptc-trial-matching/case/${encodeURIComponent(caseId)}`, {
    active_only: activeOnly,
    limit: Math.min(200, Math.max(1, limit)),
    gene,
  }))
}
