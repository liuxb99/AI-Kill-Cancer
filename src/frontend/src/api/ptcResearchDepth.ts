import { apiRequest, withQuery } from './client'

export interface OutcomeMetric {
  outcome_type: string
  observations: number
  known_binary_observations: number
  events: number
  non_events: number
  unknown_or_nonbinary: number
  event_proportion?: number | null
  missingness: number
  value_distribution: Record<string, number>
}

export interface OutcomeFeedback {
  cohort_size: number
  cases_with_outcomes: number
  outcome_coverage: number
  outcomes: OutcomeMetric[]
  research_confidence: string
  selection_boundary: string
  interpretation: string
  disclaimer: string
}

export interface CohortGroup {
  cases: number
  fraction: number
  outcome_feedback: OutcomeFeedback
}

export interface CohortStratification {
  biomarker: { gene: string; protein_change?: string | null }
  total_cases: number
  positive: CohortGroup
  negative: CohortGroup
  small_sample_warning: boolean
  analysis_type: string
  causal_inference: boolean
  disclaimer: string
}

export interface EvidenceReference {
  id: string
  source_name?: string
  source_record_id?: string
  evidence_level: string
  summary?: string
  limitations?: string
}

export interface EvidenceConflict {
  total: number
  counts: Record<string, number>
  weighted_support: number
  weighted_conflict: number
  agreement_ratio?: number | null
  conflict_severity: string
  source_diversity: number
  sources: string[]
  supports: EvidenceReference[]
  opposes: EvidenceReference[]
  unresolved_reasons: string[]
  consensus_method: string
  majority_vote_only: boolean
}

export interface ResearchHypothesis {
  id?: string
  hypothesis_key?: string
  gene_symbol?: string
  protein_change?: string | null
  hypothesis_type: string
  version?: number
  status?: string
  claim: string
  rationale: Record<string, unknown>
  supporting_observations: unknown[]
  counter_evidence: unknown[]
  uncertainties: string[]
  falsification_criteria: string
  next_data_needed: string[]
  input_fingerprint?: string
  clinical_use: false
  created_at?: string
}

export interface ResearchDepthPacket {
  biomarker: { gene: string; protein_change?: string | null }
  cohort_stratification: CohortStratification
  evidence_conflict: EvidenceConflict
  hypotheses: ResearchHypothesis[]
  trace: Array<Record<string, unknown>>
  research_only: true
  clinical_use: false
  disclaimer: string
}

export interface ResearchLoopResult {
  run_id: string
  run_key: string
  input_fingerprint: string
  reused: boolean
  trace: Array<Record<string, unknown>>
  result_summary: Record<string, unknown>
  cohort_stratification?: CohortStratification
  evidence_conflict?: EvidenceConflict
  hypotheses: ResearchHypothesis[]
  research_only: true
  clinical_use: false
  disclaimer?: string
}

export interface ResearchEvent {
  id: string
  event_key: string
  event_type: string
  gene_symbol?: string | null
  hypothesis_id?: string | null
  run_id?: string | null
  observed_at?: string | null
  date_semantics: string
  source_type: string
  source_id?: string | null
  provenance: Record<string, unknown>
  payload: Record<string, unknown>
}

export function getResearchDepthPacket(
  gene: string,
  proteinChange?: string,
): Promise<ResearchDepthPacket> {
  return apiRequest(withQuery(`/ptc-research-depth/biomarker/${encodeURIComponent(gene)}`, {
    protein_change: proteinChange || undefined,
  }))
}

export function runResearchDepthLoop(
  gene: string,
  proteinChange?: string,
): Promise<ResearchLoopResult> {
  return apiRequest(withQuery(`/ptc-research-depth/biomarker/${encodeURIComponent(gene)}/run`, {
    protein_change: proteinChange || undefined,
  }), { method: 'POST' })
}

export function listResearchHypotheses(gene?: string): Promise<{ count: number; items: ResearchHypothesis[] }> {
  return apiRequest(withQuery('/ptc-research-depth/hypotheses', { gene: gene || undefined }))
}

export function listResearchEvents(gene?: string): Promise<{ count: number; events: ResearchEvent[] }> {
  return apiRequest(withQuery('/ptc-research-depth/events', { gene: gene || undefined }))
}
