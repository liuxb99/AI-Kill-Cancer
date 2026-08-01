import { apiRequest, withQuery } from './client'

export interface PTCSourceStatus {
  cases: number
  variants: number
  outcomes: number
  therapies: number
  evidence: number
  clinical_trials: number
  herbs: number
  compounds: number
  interactions: number
  knowledge_sources: Record<string, number>
}

export interface PTCSyncStage {
  status: 'success' | 'failed' | 'skipped'
  result?: unknown
  error?: string
  reason?: string
}

export interface PTCSyncResult {
  status: 'completed' | 'completed_with_errors'
  started_at: string
  finished_at: string
  duration_seconds: number
  stages: Record<string, PTCSyncStage>
  summary: PTCSourceStatus
}

export interface PTCOutcomeByGene {
  gene: string
  case_count: number
  vital_status: Record<string, number>
  outcomes: Record<string, number>
}

export interface PTCCompleteGraph {
  generated_at: string
  node_count: number
  edge_count: number
  nodes: Array<{ id: string; type: string; label: string; properties: Record<string, unknown> }>
  edges: Array<{ id: string; source: string; target: string; relation: string; properties: Record<string, unknown> }>
}

export interface PTCReadinessResult {
  status: 'ready' | 'not_ready'
  demo_ready: boolean
  research_ready: boolean
  counts: PTCSourceStatus
  graph: {
    nodes: number
    relations: number
    dangling_edge_count: number
    dangling_edges: string[]
    knowgraph_entities: number
    knowgraph_relations: number
  }
  checks: {
    demo: Record<string, boolean>
    research: Record<string, boolean>
    structural: Record<string, boolean>
  }
  blockers: string[]
  research_gaps: string[]
  disclaimer: string
}

export interface PTCCompleteSyncPayload {
  gdc_size: number
  gdc_mutation_files: number
  trial_size: number
  pubmed_size: number
  drug_names: string[]
  include_civic: boolean
}

export function getPTCSourceStatus(): Promise<PTCSourceStatus> {
  return apiRequest('/ptc-completion/status')
}

export function getPTCReadiness(): Promise<PTCReadinessResult> {
  return apiRequest('/ptc-readiness')
}

export function getPTCOutcomesByGene(): Promise<PTCOutcomeByGene[]> {
  return apiRequest('/ptc-completion/outcomes/by-gene')
}

export function getPTCCompleteGraph(caseLimit = 500): Promise<PTCCompleteGraph> {
  return apiRequest(withQuery('/ptc-completion/graph', { case_limit: caseLimit }))
}

export function syncPTCCompletePipeline(payload: PTCCompleteSyncPayload): Promise<PTCSyncResult> {
  return apiRequest('/ptc-completion/sync-all', { method: 'POST', body: JSON.stringify(payload) })
}
