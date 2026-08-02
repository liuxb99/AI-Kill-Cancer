import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCTrialMatchingPage from '../pages/PTCTrialMatchingPage'

const { getPTCCase, getPTCTrialMatches } = vi.hoisted(() => ({
  getPTCCase: vi.fn(),
  getPTCTrialMatches: vi.fn(),
}))

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 1,
    limit: 100,
    cases: [{
      case_id: 'TCGA-TRIAL-001', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', age_range: '40-50', sex: 'Female',
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [],
    }],
  }),
}))

vi.mock('../api/ptcResearch', () => ({ getPTCCase }))
vi.mock('../api/ptcTrialMatching', () => ({ getPTCTrialMatches }))

const response = {
  case_id: 'TCGA-TRIAL-001', selected_gene: 'BRAF',
  methodology: {
    matching_version: 'ptc-trial-research-navigation-v2', score_type: 'research_relevance', maximum_score: 100,
    eligibility_separate_from_score: true, eligibility_determination: false,
    eligibility_fields: ['age', 'pathologic_stage', 'sex', 'ecog_performance_status', 'organ_function', 'prior_treatment', 'exclusion_criteria'],
    required_for_real_eligibility: ['exact_age', 'ECOG_performance_status', 'investigator_review'],
  },
  weights: { disease_relevance: 20, gene_relevance: 30, protein_variant_relevance: 20, recruitment_status: 15, site_information: 10, source_provenance: 5 },
  case_facts: { genes: ['BRAF'], variants: [], pathologic_stage: 'Stage I', age_range: '40-50', sex: 'Female' },
  summary: { total: 1, research_candidate: 1, insufficient_relevance_data: 0, low_relevance: 0, eligibility_conflict_detected: 0, eligibility_review_required: 1 },
  matches: [{
    nct_id: 'NCT-MATCH-001', title: 'BRAF V600E PTC trial', status: 'RECRUITING', phases: ['PHASE2'],
    conditions: ['Papillary Thyroid Carcinoma'], interventions: [], target_genes: ['BRAF'], locations: [{ country: 'US' }],
    source_url: 'https://clinicaltrials.gov/study/NCT-MATCH-001', score: 100,
    score_type: 'research_relevance', score_version: 'ptc-trial-research-navigation-v2',
    classification: 'research_candidate', eligibility_status: 'incomplete_review_required', eligibility_determination: false,
    relevance_criteria: [{ name: 'gene_relevance', track: 'relevance', status: 'match', weight: 30, awarded: 30, detail: 'Shared genes: BRAF', evidence: null }],
    eligibility_criteria: [{ name: 'ecog_performance_status', track: 'eligibility', status: 'unknown', weight: 0, awarded: 0, detail: 'Clinical data required.', evidence: null }],
    criteria: [], blocking_relevance_mismatches: [], eligibility_conflicts: [],
    missing_or_unverified_eligibility: ['ecog_performance_status'], missing_relevance_metadata: [],
  }],
  trace: [],
  disclaimer: 'Research navigation only. A research-candidate label is not trial eligibility.',
}

describe('PTCTrialMatchingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getPTCTrialMatches.mockResolvedValue(response)
    getPTCCase.mockResolvedValue({
      case_id: 'TCGA-ARCHIVE-999', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma', variants: [{ variant_id: 'v2', gene: 'RET' }], outcomes: [],
    })
  })

  it('separates research relevance from eligibility review', async () => {
    render(<MemoryRouter><PTCTrialMatchingPage /></MemoryRouter>)
    expect(await screen.findByRole('option', { name: /TCGA-TRIAL-001/ })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('基因筛选'), { target: { value: 'BRAF' } })
    fireEvent.click(screen.getByRole('button', { name: '开始研究比对' }))

    expect(await screen.findByText('NCT-MATCH-001 · RECRUITING')).toBeInTheDocument()
    expect(screen.getByText('研究相关度评分')).toBeInTheDocument()
    expect(screen.getByText('资格核验（不计分）')).toBeInTheDocument()
    expect(screen.getByText('不计分')).toBeInTheDocument()
    expect(screen.getByText(/资格与分数分离：是/)).toBeInTheDocument()
    expect(screen.getByText(/research-candidate label is not trial eligibility/)).toBeInTheDocument()
    expect(screen.queryByText(/符合资格/)).not.toBeInTheDocument()
    expect(getPTCTrialMatches).toHaveBeenCalledWith('TCGA-TRIAL-001', 'BRAF', true)
  })

  it('supports exact full-database case lookup', async () => {
    render(<MemoryRouter><PTCTrialMatchingPage /></MemoryRouter>)
    await screen.findByRole('option', { name: /TCGA-TRIAL-001/ })
    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    fireEvent.change(screen.getByPlaceholderText('例如 TCGA-XX-XXXX'), { target: { value: 'TCGA-ARCHIVE-999' } })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(getPTCCase).toHaveBeenCalledWith('TCGA-ARCHIVE-999'))
    expect(await screen.findByDisplayValue('TCGA-ARCHIVE-999')).toBeInTheDocument()
  })
})
