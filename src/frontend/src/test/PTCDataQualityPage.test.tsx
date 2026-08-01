import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import PTCDataQualityPage from '../pages/PTCDataQualityPage'

const mocks = vi.hoisted(() => ({
  getPTCDataQuality: vi.fn(),
  getPTCGeneQuality: vi.fn(),
}))

vi.mock('../api/ptcDataQuality', () => ({
  getPTCDataQuality: mocks.getPTCDataQuality,
  getPTCGeneQuality: mocks.getPTCGeneQuality,
}))

const response = {
  generated_at: '2026-08-01T09:00:00Z',
  inventory: { cases: 100, variants: 240, therapies: 8, evidence: 65, trials: 24, import_batches: 3 },
  sources: [
    { source_name: 'ClinicalTrials.gov', label: 'ClinicalTrials.gov', stale_after_days: 14, homepage: 'https://clinicaltrials.gov/', data_role: 'trial registry metadata', record_count: 24, last_retrieved_at: '2026-08-01T08:00:00Z', age_days: 0.04, freshness: 'fresh', missing_source_url: 0, missing_source_version: 0, failed_or_incomplete_batches: 0 },
    { source_name: 'PubMed', label: 'PubMed / PMC', stale_after_days: 30, homepage: 'https://pubmed.ncbi.nlm.nih.gov/', data_role: 'publication abstracts and open-full-text assets', record_count: 65, last_retrieved_at: '2026-06-01T08:00:00Z', age_days: 61, freshness: 'stale', missing_source_url: 2, missing_source_version: 0, failed_or_incomplete_batches: 0 },
  ],
  gene_coverage: [
    { gene: 'BRAF', case_variants: 82, therapy_targets: 3, evidence_records: 24, clinical_trials: 8, coverage_score: 4, gaps: [] },
    { gene: 'RET', case_variants: 9, therapy_targets: 1, evidence_records: 4, clinical_trials: 0, coverage_score: 3, gaps: ['no_trial'] },
  ],
  summary: { fresh_sources: 1, stale_sources: 1, missing_sources: 0, quality_issues: 2, genes_with_gaps: 1 },
  issues: [{ severity: 'warning', source: 'PubMed', code: 'source_stale' }],
  trace: [{ step: 4, name: 'emit_objective_quality_gaps', records: 3 }],
  policy_note: 'Freshness thresholds are project operational policies.',
}

describe('PTCDataQualityPage', () => {
  beforeEach(() => {
    mocks.getPTCDataQuality.mockReset()
    mocks.getPTCGeneQuality.mockReset()
    mocks.getPTCDataQuality.mockResolvedValue(response)
    mocks.getPTCGeneQuality.mockResolvedValue({
      gene: 'NTRK1',
      found: true,
      coverage: { gene: 'NTRK1', case_variants: 2, therapy_targets: 1, evidence_records: 3, clinical_trials: 1, coverage_score: 4, gaps: [] },
    })
  })

  it('shows latest coverage and supports exact gene query', async () => {
    const user = userEvent.setup()
    render(<PTCDataQualityPage />)

    expect(await screen.findByText('ClinicalTrials.gov')).toBeInTheDocument()
    expect(screen.getByText('BRAF')).toBeInTheDocument()
    expect(screen.getByText('RET')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '進階精準查詢' }))
    await user.type(screen.getByPlaceholderText(/BRAF、RET、NTRK1/), 'NTRK1')
    await user.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(mocks.getPTCGeneQuality).toHaveBeenCalledWith('NTRK1'))
    expect(await screen.findByText('進階查詢：NTRK1')).toBeInTheDocument()
  })

  it('reloads with stale-only policy', async () => {
    const user = userEvent.setup()
    render(<PTCDataQualityPage />)
    await screen.findByText('ClinicalTrials.gov')
    await user.click(screen.getByLabelText('只顯示過期或缺失來源'))
    await waitFor(() => expect(mocks.getPTCDataQuality).toHaveBeenLastCalledWith(true))
  })
})
