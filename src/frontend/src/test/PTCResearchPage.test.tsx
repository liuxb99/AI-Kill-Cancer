import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  listPTCCases: vi.fn(),
  getPTCGraphPath: vi.fn(),
}))

vi.mock('../api/ptcResearch', () => ({
  listPTCCases: mocks.listPTCCases,
  getPTCGraphPath: mocks.getPTCGraphPath,
}))

import PTCResearchPage from '../pages/PTCResearchPage'

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

function renderPage(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes><Route path="/ptc-research" element={<PTCResearchPage />} /></Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [demoCase] }),
  }))
  mocks.listPTCCases.mockResolvedValue([])
})

describe('PTCResearchPage demo hydration', () => {
  it('hydrates a synthetic demo case without querying the research database', async () => {
    renderPage('/ptc-research?demo_case=PTC-DEMO-001&data_mode=synthetic')

    expect(await screen.findByTestId('demo-context-banner')).toBeInTheDocument()
    expect(screen.getByText('PTC-DEMO-001', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('BRAF')).toBeInTheDocument()
    expect(screen.getByText('p.Val600Glu')).toBeInTheDocument()
    expect(screen.getByText('Synthetic evidence summary')).toBeInTheDocument()
    expect(screen.getByText('NCT-DEMO-001')).toBeInTheDocument()
    expect(mocks.listPTCCases).not.toHaveBeenCalled()
    expect(mocks.getPTCGraphPath).not.toHaveBeenCalled()
  })

  it('keeps the normal research database path when no demo context is present', async () => {
    renderPage('/ptc-research')
    expect(await screen.findByText('尚未匯入 PTC 病例。')).toBeInTheDocument()
    expect(mocks.listPTCCases).toHaveBeenCalledTimes(1)
  })
})
