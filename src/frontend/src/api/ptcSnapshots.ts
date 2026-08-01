import { apiRequest, withQuery } from './client'

export interface PTCSnapshot {
  schema: string
  generated_at: string
  checksum_algorithm: 'SHA-256'
  checksum_sha256: string
  content: {
    case: Record<string, unknown> & { case_id: string }
    selected_gene?: string | null
    variants: unknown[]
    outcomes: unknown[]
    therapies: unknown[]
    evidence: unknown[]
    clinical_trials: unknown[]
    import_batches: unknown[]
    counts: Record<string, number>
  }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export interface PTCSnapshotVerification {
  valid: boolean
  expected?: string | null
  actual?: string | null
  schema?: string | null
  case_id?: string | null
  reason?: string | null
}

export function createPTCSnapshot(caseId: string, gene?: string): Promise<PTCSnapshot> {
  return apiRequest(withQuery(`/ptc-snapshots/case/${encodeURIComponent(caseId)}`, { gene }))
}

export function verifyPTCSnapshot(document: unknown): Promise<PTCSnapshotVerification> {
  return apiRequest('/ptc-snapshots/verify', {
    method: 'POST',
    body: JSON.stringify(document),
  })
}
