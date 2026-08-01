import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/ptcCompletion', () => ({
  getPTCReadiness: vi.fn(),
  getPTCSourceStatus: vi.fn(),
}))

vi.mock('../api/ptcDataQuality', () => ({
  getPTCDataQuality: vi.fn(),
}))

import { getPTCReadiness, getPTCSourceStatus } from '../api/ptcCompletion'
import { getPTCDataQuality } from '../api/ptcDataQuality'
import { loadProductionReadiness } from '../api/productionReadiness'

const readiness = {
  status: 'ready',
  demo_ready: true,
  research_ready: true,
  counts: {},
  graph: {
    nodes: 12,
    relations: 18,
    dangling_edge_count: 0,
    dangling_edges: [],
    knowgraph_entities: 12,
    knowgraph_relations: 18,
  },
  checks: { demo: {}, research: {}, structural: {} },
  blockers: [],
  research_gaps: [],
  disclaimer: 'research only',
}

const sourceStatus = {
  cases: 100,
  variants: 250,
  outcomes: 100,
  therapies: 20,
  evidence: 40,
  clinical_trials: 15,
  herbs: 0,
  compounds: 0,
  interactions: 0,
  knowledge_sources: {},
}

const quality = {
  generated_at: '2026-08-01T00:00:00Z',
  inventory: {},
  sources: [],
  gene_coverage: [],
  summary: { fresh_sources: 5, stale_sources: 0, missing_sources: 0, quality_issues: 0, genes_with_gaps: 0 },
  issues: [],
  trace: [],
  policy_note: 'operations policy',
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.mocked(getPTCReadiness).mockResolvedValue(readiness as never)
  vi.mocked(getPTCSourceStatus).mockResolvedValue(sourceStatus as never)
  vi.mocked(getPTCDataQuality).mockResolvedValue(quality as never)
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ mode: 'research', version: '1.0.0', model_loaded: true, database_connected: true }),
  }))
})

describe('production readiness aggregation', () => {
  it('returns ready when platform, PTC and data sources are healthy', async () => {
    const result = await loadProductionReadiness()
    expect(result.overall).toBe('ready')
    expect(result.blockers).toEqual([])
    expect(result.warnings).toEqual([])
    expect(result.health.data?.database_connected).toBe(true)
  })

  it('returns blocked with explicit database and PTC blockers', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ mode: 'research', version: '1.0.0', model_loaded: false, database_connected: false }),
    }))
    vi.mocked(getPTCReadiness).mockResolvedValue({
      ...readiness,
      status: 'not_ready',
      blockers: ['No persisted PTC cases'],
      research_gaps: ['Evidence coverage is incomplete'],
    } as never)

    const result = await loadProductionReadiness()
    expect(result.overall).toBe('blocked')
    expect(result.blockers).toContain('Database connection is unavailable')
    expect(result.blockers).toContain('No persisted PTC cases')
    expect(result.warnings).toContain('Model is not loaded')
    expect(result.warnings).toContain('Evidence coverage is incomplete')
  })

  it('keeps a partial snapshot when data quality is unavailable', async () => {
    vi.mocked(getPTCDataQuality).mockRejectedValue(new Error('quality endpoint offline'))
    const result = await loadProductionReadiness()
    expect(result.overall).toBe('degraded')
    expect(result.data_quality.ok).toBe(false)
    expect(result.warnings).toContain('PTC data quality unavailable: quality endpoint offline')
  })
})
