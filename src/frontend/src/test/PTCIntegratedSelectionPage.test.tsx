import '@testing-library/jest-dom'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

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
vi.mock('../api/ptcResearch', () => ({ getPTCCase: vi.fn() }))
vi.mock('../api/ptcIntegrated', () => ({
  getPTCIntegratedDashboard: mocks.getPTCIntegratedDashboard,
  listPTCHerbs: mocks.listPTCHerbs,
  listPTCInteractions: mocks.listPTCInteractions,
  bootstrapPTCHerbs: mocks.bootstrapPTCHerbs,
  generatePTCIntegratedRecommendation: mocks.generatePTCIntegratedRecommendation,
  calculatePTCSimilarity: mocks.calculatePTCSimilarity,
}))

const demoCase = {
  case_key: 'PTC-DEMO-001',
  display_name: 'Synthetic BRAF Case',
  cancer_type: 'Papillary Thyroid Carcinoma',
  stage: 'Stage III',
  radioiodine_status: 'refractory',
  variant: { gene: 'BRAF', hgvs_p: 'p.Val600Glu', variant_type: 'SNV', driver_status: 'driver' },
  drug: { name: 'Demo Drug', mechanism: 'Synthetic MAPK pathway example' },
  evidence: { level: 'A', direction: 'supports', summary: 'Synthetic evidence summary', synthetic: true },
  publication: { title: 'Synthetic PTC Publication', journal: 'Demo Journal' },
  clinical_trial: { id: 'NCT-DEMO-001', title: 'Synthetic Trial', status: 'RECRUITING' },
}

function renderPage(initialEntry = '/ptc-integrated') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes><Route path="/ptc-integrated" element={<PTCIntegratedPage />} /></Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [demoCase] }),
  }))
})

describe('PTCIntegratedPage latest database selection', () => {
  it('loads only the latest 100 cases and exposes no text query field in recent mode', async () => {
    mocks.getLatestPTCCases.mockResolvedValue({ count: 1, limit: 100, cases: [{ case_id: 'TCGA-WORK-001', pathologic_stage: 'Stage II', variants: [] }] })
    mocks.getPTCIntegratedDashboard.mockResolvedValue({ case_count: 1, variant_count: 0, therapy_count: 0, evidence_count: 0, trial_count: 0, herb_count: 0, interaction_count: 0, top_genes: [] })
    mocks.listPTCHerbs.mockResolvedValue([])
    mocks.listPTCInteractions.mockResolvedValue([])

    renderPage()

    const caseSelect = await screen.findByRole('combobox')
    expect(within(caseSelect).getByRole('option', { name: /TCGA-WORK-001/ })).toBeInTheDocument()
    expect(mocks.getLatestPTCCases).toHaveBeenCalledWith(100)
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('hydrates synthetic demo context without calling research workbench APIs', async () => {
    renderPage('/ptc-integrated?demo_case=PTC-DEMO-001&data_mode=synthetic')

    expect(await screen.findByTestId('demo-context-banner')).toBeInTheDocument()
    expect(screen.getByText('PTC-DEMO-001', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('BRAF')).toBeInTheDocument()
    expect(screen.getByText('Synthetic evidence summary')).toBeInTheDocument()
    expect(screen.getByText('NCT-DEMO-001')).toBeInTheDocument()
    expect(screen.getByText(/Demo isolation/)).toBeInTheDocument()

    expect(mocks.getPTCIntegratedDashboard).not.toHaveBeenCalled()
    expect(mocks.getLatestPTCCases).not.toHaveBeenCalled()
    expect(mocks.listPTCHerbs).not.toHaveBeenCalled()
    expect(mocks.listPTCInteractions).not.toHaveBeenCalled()
    expect(mocks.generatePTCIntegratedRecommendation).not.toHaveBeenCalled()
    expect(mocks.calculatePTCSimilarity).not.toHaveBeenCalled()
  })
})
