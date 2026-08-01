export interface PTCSourceQuality {
  source_name: string
  label: string
  stale_after_days: number
  homepage: string
  data_role: string
  record_count: number
  last_retrieved_at?: string
  age_days?: number
  freshness: 'fresh' | 'stale' | 'missing'
  missing_source_url: number
  missing_source_version: number
  failed_or_incomplete_batches: number
}

export interface PTCGeneCoverage {
  gene: string
  case_variants: number
  therapy_targets: number
  evidence_records: number
  clinical_trials: number
  coverage_score: number
  gaps: string[]
}

export interface PTCDataQualityOverview {
  generated_at: string
  inventory: Record<string, number>
  sources: PTCSourceQuality[]
  gene_coverage: PTCGeneCoverage[]
  summary: {
    fresh_sources: number
    stale_sources: number
    missing_sources: number
    quality_issues: number
    genes_with_gaps: number
  }
  issues: Array<{ severity: string; source: string; code: string; count?: number }>
  trace: Array<{ step: number; name: string; records: number }>
  policy_note: string
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export function getPTCDataQuality(staleOnly = false): Promise<PTCDataQualityOverview> {
  return request(`/ptc-data-quality/overview?stale_only=${staleOnly}`)
}

export function getPTCGeneQuality(gene: string): Promise<{ gene: string; found: boolean; coverage: PTCGeneCoverage }> {
  return request(`/ptc-data-quality/gene/${encodeURIComponent(gene)}`)
}
