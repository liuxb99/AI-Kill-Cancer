import { apiRequest } from './client'

export interface PTCTargetTherapy {
  therapy_key: string
  name: string
  generic_name?: string
  therapy_type: string
  approval_status?: string
  mechanism?: string
  indications: string[]
  source_name: string
  source_url?: string
  matched_targets: Array<{ gene: string; variant?: string; interaction_type?: string; evidence_level?: string }>
}

export interface PTCTargetingResponse {
  gene: string
  pathway: {
    pathway: string
    protein_domain: string
    domain_range?: [number, number]
    hotspots: Record<string, number>
    downstream: string[]
    therapy_classes: string[]
  }
  therapies: PTCTargetTherapy[]
  evidence: Array<{
    evidence_key: string
    source_name: string
    title?: string
    summary?: string
    evidence_level?: string
    direction?: string
    variant?: string
    citation?: string
    source_url?: string
  }>
  trials: Array<{
    nct_id: string
    brief_title: string
    overall_status?: string
    phases: string[]
    interventions: unknown[]
    source_url?: string
  }>
  counts: { therapies: number; evidence: number; trials: number }
  disclaimer: string
}

export function getPTCTargeting(gene: string): Promise<PTCTargetingResponse> {
  return apiRequest(`/ptc-targeting/gene/${encodeURIComponent(gene)}`)
}
