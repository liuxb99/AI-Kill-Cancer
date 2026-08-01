import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import PTCIntegratedPage from '../pages/PTCIntegratedPage'

const mocks = vi.hoisted(() => ({
  getLatestPTCCases: vi.fn(),
  getPTCIntegratedDashboard: vi.fn(),
  listPTCHerbs: vi.fn(),
  listPTCInteractions: vi.fn(),
  bootstrapPTCHerbs: vi.fn(),
  generatePTCIntegratedRecommendation: vi.fn(),
  calculatePTCSimilarity: vi.fn(),
}))

vi.mock('../api/ptcVisualization', () => ({ getLatestPTCCases: mocks.getLatestPTCCases }))
vi.mock('../api/ptcIntegrated', () => ({
  getPTCIntegratedDashboard: mocks.getPTCIntegratedDashboard,
  listPTCHerbs: mocks.listPTCHerbs,
  listPTCInteractions: mocks.listPTCInteractions,
  bootstrapPTCHerbs: mocks.bootstrapPTCHerbs,
  generatePTCIntegratedRecommendation: mocks.generatePTCIntegratedRecommendation,
  calculatePTCSimilarity: mocks.calculatePTCSimilarity,
}))

describe('PTCIntegratedPage latest database selection', () => {
  it('loads only the latest 100 cases and exposes no text query field', async () => {
    mocks.getLatestPTCCases.mockResolvedValue({ count: 1, limit: 100, cases: [{ case_id: 'TCGA-WORK-001', pathologic_stage: 'Stage II', variants: [] }] })
    mocks.getPTCIntegratedDashboard.mockResolvedValue({ case_count: 1, variant_count: 0, therapy_count: 0, evidence_count: 0, trial_count: 0, herb_count: 0, interaction_count: 0, top_genes: [] })
    mocks.listPTCHerbs.mockResolvedValue([])
    mocks.listPTCInteractions.mockResolvedValue([])

    render(<PTCIntegratedPage />)

    expect(await screen.findByDisplayValue('TCGA-WORK-001')).toBeInTheDocument()
    expect(mocks.getLatestPTCCases).toHaveBeenCalledWith(100)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })
})
