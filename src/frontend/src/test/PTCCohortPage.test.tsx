import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCCohortPage from '../pages/PTCCohortPage'

const navigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 2,
    limit: 100,
    cases: [
      { case_id: 'TCGA-ANCHOR', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [] },
      { case_id: 'TCGA-MATCH', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', variants: [{ variant_id: 'v2', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [] },
    ],
  }),
}))

vi.mock('../api/ptcCohort', () => ({
  getPTCSimilarCases: vi.fn().mockResolvedValue({
    anchor: { case_id: 'TCGA-ANCHOR', source_dataset: 'TCGA-THCA', pathologic_stage: 'Stage I', tnm: ['T1', 'N0', 'M0'], genes: ['BRAF'], protein_variants: ['BRAF:P.V600E'] },
    weights: { genes: 40, protein_variants: 20 },
    matches: [{
      case_id: 'TCGA-MATCH', source_dataset: 'TCGA-THCA', score: 100,
      components: { genes: 40, protein_variants: 20, pathologic_stage: 15, tnm: 10, age_range: 5, sex: 5, vital_status: 5 },
      shared_genes: ['BRAF'], shared_protein_variants: ['BRAF:P.V600E'],
      case_facts: { pathologic_stage: 'Stage I', tnm: ['T1', 'N0', 'M0'], vital_status: 'Alive', genes: ['BRAF'], variants: [], outcomes: [] },
    }],
    cohort: { size: 1, stage_distribution: { 'Stage I': 1 }, vital_status_distribution: { Alive: 1 }, top_genes: [{ gene: 'BRAF', cases: 1 }], outcome_distribution: {}, mean_follow_up_days: 1200 },
    trace: [{ step: 1, name: 'load_deidentified_cases', records: 2 }],
    disclaimer: 'Research cohort navigation only.',
  }),
}))

describe('PTCCohortPage', () => {
  it('compares cases and opens linked research tools', async () => {
    render(<MemoryRouter><PTCCohortPage /></MemoryRouter>)

    expect(await screen.findByDisplayValue('TCGA-ANCHOR')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '寻找相似病例' }))

    expect(await screen.findByText('TCGA-MATCH')).toBeInTheDocument()
    expect(screen.getByText('100.0')).toBeInTheDocument()
    expect(screen.getByText(/共同基因：/)).toHaveTextContent('BRAF')
    expect(screen.getByText('Stage I')).toBeInTheDocument()
    expect(screen.getByText('1200')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '打开 3D' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/ptc-3d?case=TCGA-MATCH'))
  })
})
