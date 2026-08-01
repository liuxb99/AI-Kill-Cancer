import { apiRequest, withQuery } from './client'

export interface PTCEvidenceMatrixRow {
  gene: string
  variants: Array<{ variant_id: string; protein_change?: string; classification?: string }>
  protein_domain?: string
  pathway?: string
  score: number
  score_type: 'data_linkage_completeness'
  score_version: string
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
    role: 'post_score_descriptive_only'
    excluded_from_score: true
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
  methodology: {
    scoring_version: string
    score_type: 'data_linkage_completeness'
    maximum_score: number
    weights: Record<string, number>
    outcome_blind: boolean
    outcome_fields_excluded: string[]
    cohort_usage: 'post_score_descriptive_summary_only'
  }
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

export function getPTCEvidenceMatrix(caseId: string, gene?: string): Promise<PTCEvidenceMatrixResponse> {
  return apiRequest(withQuery(`/ptc-evidence-matrix/case/${encodeURIComponent(caseId)}`, { gene }))
}
