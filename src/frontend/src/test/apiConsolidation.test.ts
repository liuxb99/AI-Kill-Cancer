import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  addTumorBoardVote,
  fetchPatientGraphThread,
  getActivityLog,
  getKnowledgeGraph,
} from '../api/workbench'
import {
  getCancerStats,
  getDashboardKPIs,
  getPredictionResults,
  getResearchTrends,
} from '../api/dashboard'
import {
  listResearchUploads,
  listSandboxHistory,
  runResearchSandbox,
  submitResearchPaper,
} from '../api/researchPortal'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  localStorage.clear()
})

function jsonResponse(body: unknown = {}) {
  return { ok: true, status: 200, json: async () => body }
}

describe('consolidated API clients', () => {
  it('encodes workbench identifiers and query parameters through the shared client', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await getKnowledgeGraph('CASE / 1')
    await getActivityLog('CASE / 1', 100)
    await fetchPatientGraphThread('PATIENT / 1')

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/workbench/graph/case/CASE%20%2F%201')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/workbench/activity/CASE%20%2F%201?limit=100')
    expect(fetchMock.mock.calls[2][0]).toBe('/api/v1/clinical-graph/patient/PATIENT%20%2F%201/thread')
  })

  it('serializes workbench mutation bodies exactly once', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', review_id: 'r1' }))
    vi.stubGlobal('fetch', fetchMock)

    await addTumorBoardVote('CASE-1', { vote: 'support', rationale: 'evidence' })

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/workbench/tumor-board/CASE-1/vote', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ vote: 'support', rationale: 'evidence' }),
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }))
  })

  it('uses the four same-origin dashboard endpoints', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)

    await getDashboardKPIs()
    await getCancerStats()
    await getPredictionResults()
    await getResearchTrends()

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/v1/dashboard/kpis',
      '/api/v1/charts/cancer-stats',
      '/api/v1/charts/prediction-results',
      '/api/v1/charts/research-trends',
    ])
  })

  it('uses shared research portal endpoints and JSON bodies', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]))
    vi.stubGlobal('fetch', fetchMock)

    await listResearchUploads()
    await listSandboxHistory()
    await submitResearchPaper({ title: 'PTC', authors: 'A', journal: '', year: '2026', doi: '', abstract: 'A', keywords: 'BRAF' })
    await runResearchSandbox({ gene: 'BRAF' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/research/uploads')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/research/sandbox-history')
    expect(fetchMock.mock.calls[2][0]).toBe('/api/v1/research/papers')
    expect(fetchMock.mock.calls[2][1]).toEqual(expect.objectContaining({ method: 'POST', body: expect.any(String) }))
    expect(fetchMock.mock.calls[3][0]).toBe('/api/v1/predict')
  })
})

function sourceFiles(root: string): string[] {
  const files: string[] = []
  for (const name of readdirSync(root)) {
    const path = join(root, name)
    const rel = relative(process.cwd(), path).replaceAll('\\', '/')
    if (rel.includes('/test/') || rel.endsWith('/api/client.ts')) continue
    if (statSync(path).isDirectory()) files.push(...sourceFiles(path))
    else if (/\.(ts|tsx)$/.test(name)) files.push(path)
  }
  return files
}

describe('source-level API architecture guard', () => {
  it('contains no environment API base or parallel API_BASE implementation', () => {
    const violations: string[] = []
    for (const file of sourceFiles(join(process.cwd(), 'src'))) {
      const source = readFileSync(file, 'utf8')
      if (source.includes('VITE_API_URL') || /\bconst\s+API_BASE\b/.test(source)) {
        violations.push(relative(process.cwd(), file).replaceAll('\\', '/'))
      }
    }
    expect(violations).toEqual([])
  })
})
