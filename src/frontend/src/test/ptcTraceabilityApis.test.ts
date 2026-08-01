import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createPTCSnapshot, verifyPTCSnapshot } from '../api/ptcSnapshots'
import { getPTCCaseTimeline } from '../api/ptcTimeline'

describe('PTC traceability API contracts', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads a gene-filtered timeline through the shared same-origin client', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
      case_id: 'TCGA A/1',
      selected_gene: 'BRAF V600E',
      genes: ['BRAF'],
      count: 0,
      events: [],
      summary: { by_type: {} },
      trace: [],
      disclaimer: 'research only',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await getPTCCaseTimeline('TCGA A/1', 'BRAF V600E')

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/ptc-timeline/case/TCGA%20A%2F1?gene=BRAF+V600E',
      expect.objectContaining({ headers: expect.any(Object) }),
    )
  })

  it('creates a reproducible snapshot with encoded case and gene values', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
      schema: 'ptc-snapshot-v1',
      generated_at: '2026-08-01T00:00:00Z',
      checksum_algorithm: 'SHA-256',
      checksum_sha256: 'abc',
      content: {
        case: { case_id: 'TCGA/1' },
        variants: [], outcomes: [], therapies: [], evidence: [], clinical_trials: [], import_batches: [], counts: {},
      },
      trace: [],
      disclaimer: 'research only',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await createPTCSnapshot('TCGA/1', 'RET fusion')

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/ptc-snapshots/case/TCGA%2F1?gene=RET+fusion',
      expect.objectContaining({ headers: expect.any(Object) }),
    )
  })

  it('verifies snapshots with one JSON serialization and authorization support', async () => {
    localStorage.setItem('auth_token', 'trace-token')
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ valid: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))
    const document = { schema: 'ptc-snapshot-v1', checksum_sha256: 'abc' }

    await verifyPTCSnapshot(document)

    expect(fetch).toHaveBeenCalledWith('/api/v1/ptc-snapshots/verify', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(document),
      headers: expect.objectContaining({
        Authorization: 'Bearer trace-token',
        'Content-Type': 'application/json',
      }),
    }))
  })
})
