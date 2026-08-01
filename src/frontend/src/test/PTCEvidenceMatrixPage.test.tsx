import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCEvidenceMatrixPage from '../pages/PTCEvidenceMatrixPage'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 1,
    limit: 100,
    cases: [{
      case_id: 'TCGA-MATRIX-001',
      source_dataset: 'TCGA-THCA',
      source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma',
      pathologic_stage: 'Stage I',
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
      outcomes: [],
    }],
  }),
}))

vi.mock('../api/ptcEvidenceMatrix', () => ({
  getPTCEvidenceMatrix: vi.fn().mockResolvedValue({
    case_id: 'TCGA-MATRIX-001',
    source_dataset: 'TCGA-THCA',
    pathologic_stage: 'Stage I',
    rows: [{
      gene: 'BRAF',
      variants: [{ variant_id: 'v1', protein_change: 'p.V600E', classification: 'Missense_Mutation' }],
      protein_domain: 'Kinase domain',
      pathway: 'MAPK / ERK',
      score: 92,
      score_components: { variant_present: 20, persisted_therapies: 5, best_evidence_level: 30, active_trials: 5, open_full_text_assets: 4, same_gene_cohort: 0.5 },
      therapies: [{ therapy_key: 't1', name: 'Dabrafenib', approval_status: 'FDA label available', mechanism: 'BRAF inhibitor' }],
      evidence: [{ evidence_key: 'e1', title: 'BRAF evidence', source: 'PubMed', level: 'A', figures: 1, tables: 1 }],
      trials: [{ nct_id: 'NCT-MATRIX-001', title: 'BRAF trial', status: 'RECRUITING', active: true }],
      cohort: { same_gene_cases: 12, vital_status_distribution: { Alive: 10, Dead: 2 }, outcome_distribution: {} },
      assets: { figures: 1, tables: 1 },
      gaps: [],
    }],
    summary: { genes: 1, therapies: 1, evidence: 1, trials: 1, open_full_text_assets: 2, unresolved_gaps: 0 },
    trace: [],
    disclaimer: 'Research evidence navigation only.',
  }),
}))

describe('PTCEvidenceMatrixPage', () => {
  it('renders the evidence chain and opens linked tools', async () => {
    render(<MemoryRouter><PTCEvidenceMatrixPage /></MemoryRouter>)

    expect(await screen.findByDisplayValue('TCGA-MATRIX-001')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '生成证据矩阵' }))

    expect(await screen.findByText('Dabrafenib')).toBeInTheDocument()
    expect(screen.getByText('BRAF evidence')).toBeInTheDocument()
    expect(screen.getByText('NCT-MATRIX-001')).toBeInTheDocument()
    expect(screen.getByText('12 cases')).toBeInTheDocument()
    expect(screen.getByText('92.0')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '蛋白 3D' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/ptc-3d?case=TCGA-MATRIX-001&gene=BRAF&view=protein'))
  })
})
