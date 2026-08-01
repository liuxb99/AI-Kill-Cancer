import { afterEach, describe, expect, it, vi } from 'vitest'

import { getLatestPTCCases, getPTCProteinStructure } from '../api/ptcVisualization'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('PTC visualization API URLs', () => {
  it('uses a same-origin relative URL for the latest 100 cases', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ count: 0, limit: 100, cases: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await getLatestPTCCases(100)

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/ptc-visualization/cases/latest?limit=100')
  })

  it('encodes gene names and keeps protein requests same-origin', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ gene: 'RET FUSION' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await getPTCProteinStructure('RET FUSION')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/ptc-visualization/proteins/RET%20FUSION')
  })

  it('reports the attempted path when Safari rejects a request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException(
      'The string did not match the expected pattern.',
      'SyntaxError',
    )))

    await expect(getLatestPTCCases()).rejects.toThrow(
      'PTC API request failed (/api/v1/ptc-visualization/cases/latest?limit=100)',
    )
  })
})
