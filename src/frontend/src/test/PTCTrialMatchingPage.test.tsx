import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCTrialMatchingPage from '../pages/PTCTrialMatchingPage'

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 1,
    limit: 100,
    cases: [{
      case_id: 'TCGA-TRIAL-001', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I',
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [],
    }],
  }),
}))

vi.mock('../api/ptcTrialMatching', () => ({
  getPTCTrialMatches: vi.fn().mockResolvedValue({
    case_id: 'TCGA-TRIAL-001', selected_gene: 'BRAF',
    case_facts: { genes: ['BRAF'], variants: [], pathologic_stage: 'Stage I', age_range: '40-50', sex: 'Female' },
    summary: { total: 1, potential_match: 1, insufficient_data: 0, unlikely_match: 0 },
    matches: [{
      nct_id: 'NCT-MATCH-001', title: 'BRAF V600E PTC trial', status: 'RECRUITING', phases: ['PHASE2'],
      conditions: ['Papillary Thyroid Carcinoma'], interventions: [], target_genes: ['BRAF'],
      source_url: 'https://clinicaltrials.gov/study/NCT-MATCH-001', score: 90,
      classification: 'potential_match', blocking_mismatches: [], missing_or_unparsed: ['sex'],
      criteria: [
        { name: 'gene', status: 'match', weight: 25, awarded: 25, detail: 'Shared genes: BRAF', evidence: null },
        { name: 'age', status: 'match', weight: 10, awarded: 10, detail: 'Case age 40-50', evidence: null },
        { name: 'sex', status: 'unknown', weight: 5, awarded: 0, detail: 'No exclusive restriction', evidence: null },
      ],
    }],
    trace: [],
    disclaimer: 'Research navigation only. This output is not a determination of trial eligibility.',
  }),
}))

describe('PTCTrialMatchingPage', () => {
  it('shows explainable trial metadata alignment', async () => {
    render(<MemoryRouter><PTCTrialMatchingPage /></MemoryRouter>)
    expect(await screen.findByDisplayValue('TCGA-TRIAL-001')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('基因筛选'), { target: { value: 'BRAF' } })
    fireEvent.click(screen.getByRole('button', { name: '开始试验比对' }))
    expect(await screen.findByText('NCT-MATCH-001 · RECRUITING')).toBeInTheDocument()
    expect(screen.getByText('BRAF V600E PTC trial')).toBeInTheDocument()
    expect(screen.getByText('Shared genes: BRAF')).toBeInTheDocument()
    expect(screen.getByText(/not a determination of trial eligibility/)).toBeInTheDocument()
  })
})
