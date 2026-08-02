import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCCohortPage from '../pages/PTCCohortPage'

const { navigate, getPTCCase, getPTCSimilarCases } = vi.hoisted(() => ({ navigate: vi.fn(), getPTCCase: vi.fn(), getPTCSimilarCases: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({ count: 2, limit: 100, cases: [
    { case_id: 'TCGA-ANCHOR', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [] },
    { case_id: 'TCGA-MATCH', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', variants: [{ variant_id: 'v2', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [] },
  ] }),
}))
vi.mock('../api/ptcResearch', () => ({ getPTCCase }))
vi.mock('../api/ptcCohort', () => ({ getPTCSimilarCases }))

const response = {
  anchor: { case_id: 'TCGA-ANCHOR', source_dataset: 'TCGA-THCA', pathologic_stage: 'Stage I', tnm: ['T1', 'N0', 'M0'], genes: ['BRAF'], protein_variants: ['BRAF:P.V600E'] },
  methodology: { scoring_version: 'ptc-cohort-outcome-blind-v2', outcome_blind: true, outcome_fields_excluded: ['vital_status', 'days_to_last_follow_up', 'days_to_death', 'outcomes'], outcome_usage: 'post_match_descriptive_summary_only', candidate_window: 2 },
  weights: { genes: 42, protein_variants: 23, pathologic_stage: 15, tnm: 10, age_range: 5, sex: 5 },
  matches: [{ case_id: 'TCGA-MATCH', source_dataset: 'TCGA-THCA', score: 100, components: { genes: 42, protein_variants: 23, pathologic_stage: 15, tnm: 10, age_range: 5, sex: 5 }, shared_genes: ['BRAF'], shared_protein_variants: ['BRAF:P.V600E'], case_facts: { pathologic_stage: 'Stage I', tnm: ['T1', 'N0', 'M0'], vital_status: 'Alive', genes: ['BRAF'], variants: [], outcomes: [] } }],
  cohort: { size: 1, stage_distribution: { 'Stage I': 1 }, vital_status_distribution: { Alive: 1 }, top_genes: [{ gene: 'BRAF', cases: 1 }], outcome_distribution: {}, mean_follow_up_days: 1200, outcomes_used_for_ranking: false },
  trace: [{ step: 1, name: 'load_deidentified_cases', records: 2 }], disclaimer: 'Matching is outcome-blind.',
}

beforeEach(() => {
  navigate.mockReset(); getPTCCase.mockReset(); getPTCSimilarCases.mockReset()
  getPTCSimilarCases.mockResolvedValue(response)
  getPTCCase.mockResolvedValue({ case_id: 'TCGA-EXACT', variants: [], outcomes: [] })
  window.history.replaceState({}, '', '/ptc-cohort')
})

describe('PTCCohortPage', () => {
  it('shows outcome-blind methodology and excludes vital status from score components', async () => {
    render(<MemoryRouter><PTCCohortPage /></MemoryRouter>)
    const selects = await screen.findAllByRole('combobox')
    expect(within(selects[0]).getByRole('option', { name: /TCGA-ANCHOR/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '尋找相似病例' }))

    expect(await screen.findByText('TCGA-MATCH')).toBeInTheDocument()
    expect(screen.getByText('Outcome-blind 配對已啟用')).toBeInTheDocument()
    expect(screen.getByText(/ptc-cohort-outcome-blind-v2/)).toBeInTheDocument()
    expect(screen.getByText('vital_status')).toBeInTheDocument()
    expect(screen.queryByText(/vital_status: 5/)).not.toBeInTheDocument()
    expect(screen.getByText('100.0')).toBeInTheDocument()
    expect(screen.getByText(/共同基因：/)).toHaveTextContent('BRAF')
    expect(screen.getByText('1200')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '開啟 3D' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/ptc-3d?case=TCGA-MATCH'))
  })

  it('supports exact full-database case lookup in advanced mode', async () => {
    render(<MemoryRouter><PTCCohortPage /></MemoryRouter>)
    const selects = await screen.findAllByRole('combobox')
    expect(within(selects[0]).getByRole('option', { name: /TCGA-ANCHOR/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    fireEvent.change(screen.getByPlaceholderText('例如 TCGA-XX-XXXX'), { target: { value: 'TCGA-EXACT' } })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(getPTCCase).toHaveBeenCalledWith('TCGA-EXACT'))
    fireEvent.click(screen.getByRole('button', { name: '尋找相似病例' }))
    await waitFor(() => expect(getPTCSimilarCases).toHaveBeenCalledWith('TCGA-EXACT', 20, 0))
  })
})
