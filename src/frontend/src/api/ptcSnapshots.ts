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

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export async function createPTCSnapshot(caseId: string, gene?: string): Promise<PTCSnapshot> {
  const query = gene ? `?gene=${encodeURIComponent(gene)}` : ''
  return parse(fetch(`/api/v1/ptc-snapshots/case/${encodeURIComponent(caseId)}${query}`))
}

export async function verifyPTCSnapshot(document: unknown): Promise<PTCSnapshotVerification> {
  return parse(fetch('/api/v1/ptc-snapshots/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(document),
  }))
}
