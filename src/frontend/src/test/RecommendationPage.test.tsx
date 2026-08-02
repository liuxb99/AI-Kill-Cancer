import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiRequestMock = vi.fn()

vi.mock('../api/client', () => ({
  apiRequest: apiRequestMock,
}))

import { fetchRecommendation } from '../pages/RecommendationPage'

describe('RecommendationPage — shared API contract', () => {
  beforeEach(() => {
    apiRequestMock.mockReset()
  })

  it('posts the recommendation payload through the shared API client', async () => {
    apiRequestMock.mockResolvedValue({
      recommendation_id: 'rec-1',
      patient_id: 'TCGA-TEST',
      recommendations: [],
      trace_id: 'trace-1',
      engine_version: '1.0.0',
      created_at: '2026-08-01T00:00:00Z',
    })

    await fetchRecommendation('TCGA-TEST', ['BRAF V600E'], 5)

    expect(apiRequestMock).toHaveBeenCalledWith('/recommendation', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: 'TCGA-TEST',
        variants: ['BRAF V600E'],
        top_n: 5,
      }),
    })
  })

  it('propagates shared-client failures without replacing their detail', async () => {
    apiRequestMock.mockRejectedValue(new Error('Invalid variants'))

    await expect(fetchRecommendation('TCGA-TEST', ['BAD'], 5)).rejects.toThrow('Invalid variants')
  })
})

describe('RecommendationPage — dual-mode and consolidation guards', () => {
  it('keeps the route registered', async () => {
    const fs = await import('fs')
    const appSource = fs.readFileSync('./src/App.tsx', 'utf8')

    expect(appSource).toContain('/recommendation')
    expect(appSource).toContain('RecommendationPage')
  })

  it('uses the recent-100 plus advanced-ID selector contract', async () => {
    const fs = await import('fs')
    const source = fs.readFileSync('./src/pages/RecommendationPage.tsx', 'utf8')

    expect(source).toContain('getLatestPTCCases(100)')
    expect(source).toContain('<DualModeSelector')
    expect(source).toContain('onAdvancedQuery={useAdvancedInput}')
    expect(source).toContain('queryLabel="自訂 Patient ID"')
  })

  it('does not reintroduce direct API fetch or legacy API-base configuration', async () => {
    const fs = await import('fs')
    const source = fs.readFileSync('./src/pages/RecommendationPage.tsx', 'utf8')

    expect(source).not.toContain('VITE_API_URL')
    expect(source).not.toMatch(/fetch\s*\(/)
    expect(source).toContain("apiRequest<RecommendationResult>('/recommendation'")
  })
})
