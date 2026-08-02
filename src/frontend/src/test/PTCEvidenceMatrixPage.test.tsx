import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCEvidenceMatrixPage from '../pages/PTCEvidenceMatrixPage'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({ count: 1, limit: 100, cases: [{ case_id: 'TCGA-MATRIX-001', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', pathologic_stage: 'Stage I', variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }], outcomes: [] }] }),
}))

vi.mock('../api/ptcResearch', () => ({
  getPTCCase: vi.fn().mockResolvedValue({ case_id: 'TCGA-MATRIX-999', source_dataset: 'TCGA-THCA', source_project: 'TCGA-THCA', disease: 'papillary_thyroid_carcinoma', variants: [{ variant_id: 'v9', gene: 'RET', protein_change: 'fusion' }], outcomes: [] }),
}))

vi.mock('../api/ptcEvidenceMatrix', () => ({
  getPTCEvidenceMatrix: vi.fn().mockResolvedValue({
    case_id: 'TCGA-MATRIX-001', source_dataset: 'TCGA-THCA', pathologic_stage: 'Stage I',
    methodology: { scoring_version: 'ptc-evidence-linkage-v2', score_type: 'data_linkage_completeness', maximum_score: 100, weights: { variant_present: 20, persisted_therapies: 20, best_evidence_level: 30, active_trials: 15, open_full_text_assets: 10, source_provenance: 5 }, outcome_blind: true, outcome_fields_excluded: ['vital_status', 'days_to_last_follow_up', 'days_to_death', 'outcomes'], cohort_usage: 'post_score_descriptive_summary_only' },
    rows: [{ gene: 'BRAF', variants: [{ variant_id: 'v1', protein_change: 'p.V600E', classification: 'Missense_Mutation' }], protein_domain: 'Kinase domain', pathway: 'MAPK / ERK', score: 69, score_type: 'data_linkage_completeness', score_version: 'ptc-evidence-linkage-v2', score_components: { variant_present: 20, persisted_therapies: 5, best_evidence_level: 30, active_trials: 5, open_full_text_assets: 4, source_provenance: 5 }, therapies: [{ therapy_key: 't1', name: 'Dabrafenib', approval_status: 'FDA label available', mechanism: 'BRAF inhibitor' }], evidence: [{ evidence_key: 'e1', title: 'BRAF evidence', source: 'PubMed', level: 'A', figures: 1, tables: 1 }], trials: [{ nct_id: 'NCT-MATRIX-001', title: 'BRAF trial', status: 'RECRUITING', active: true }], cohort: { role: 'post_score_descriptive_only', excluded_from_score: true, same_gene_cases: 12, vital_status_distribution: { Alive: 10, Dead: 2 }, outcome_distribution: {} }, assets: { figures: 1, tables: 1 }, gaps: [] }],
    summary: { genes: 1, therapies: 1, evidence: 1, trials: 1, open_full_text_assets: 2, unresolved_gaps: 0 }, trace: [], disclaimer: 'Scores measure imported data linkage and provenance completeness.',
  }),
}))

describe('PTCEvidenceMatrixPage', () => {
  it('renders outcome-blind linkage scoring and opens linked tools', async () => {
    render(<MemoryRouter><PTCEvidenceMatrixPage /></MemoryRouter>)

    const selects = await screen.findAllByRole('combobox')
    expect(within(selects[0]).getByRole('option', { name: /TCGA-MATRIX-001/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '最近 100 筆' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '進階精準查詢' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '生成證據矩陣' }))

    expect(await screen.findByText('Dabrafenib')).toBeInTheDocument()
    expect(screen.getByText('BRAF evidence')).toBeInTheDocument()
    expect(screen.getByText('NCT-MATRIX-001')).toBeInTheDocument()
    expect(screen.getByText('12 cases')).toBeInTheDocument()
    expect(screen.getByText('69.0')).toBeInTheDocument()
    expect(screen.getByText('資料鏈結完整度')).toBeInTheDocument()
    expect(screen.getByText(/Outcome-blind：是/)).toBeInTheDocument()
    expect(screen.getByText(/Vital status，不參與分數/)).toBeInTheDocument()
    expect(screen.queryByText(/same_gene_cohort:/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '蛋白 3D' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/ptc-3d?case=TCGA-MATRIX-001&gene=BRAF&view=protein'))
  })

  it('supports an exact case id outside the recent 100 list', async () => {
    render(<MemoryRouter><PTCEvidenceMatrixPage /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: '進階精準查詢' }))
    const input = screen.getByPlaceholderText('例如 TCGA-XX-XXXX')
    fireEvent.change(input, { target: { value: 'TCGA-MATRIX-999' } })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(input).toHaveValue('TCGA-MATRIX-999'))
  })
})
