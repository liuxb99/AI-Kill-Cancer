import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getResearchDepthPacket: vi.fn(),
  listResearchHypotheses: vi.fn(),
  listResearchEvents: vi.fn(),
  runResearchDepthLoop: vi.fn(),
}))

vi.mock('../api/ptcResearchDepth', () => mocks)

import PTCResearchDepthPage from '../pages/PTCResearchDepthPage'

const hypothesis = {
  id: 'hyp-1',
  hypothesis_key: 'key-1',
  gene_symbol: 'BRAF',
  protein_change: 'p.V600E',
  hypothesis_type: 'cohort_outcome_association',
  version: 1,
  status: 'open',
  claim: 'BRAF-positive PTC research cases may show a higher descriptive recurrence proportion.',
  rationale: { outcome_type: 'recurrence' },
  supporting_observations: [],
  counter_evidence: [],
  uncertainties: ['small_sample'],
  falsification_criteria: 'Independent cohort does not reproduce the association.',
  next_data_needed: ['independent cohort'],
  input_fingerprint: 'abcdef1234567890',
  clinical_use: false as const,
}

const packet = {
  biomarker: { gene: 'BRAF', protein_change: 'p.V600E' },
  cohort_stratification: {
    biomarker: { gene: 'BRAF', protein_change: 'p.V600E' },
    total_cases: 20,
    positive: {
      cases: 8,
      fraction: 0.4,
      outcome_feedback: {
        cohort_size: 8,
        cases_with_outcomes: 6,
        outcome_coverage: 0.75,
        outcomes: [{ outcome_type: 'recurrence', observations: 6, known_binary_observations: 6, events: 3, non_events: 3, unknown_or_nonbinary: 0, event_proportion: 0.5, missingness: 0, value_distribution: {} }],
        research_confidence: 'moderate', selection_boundary: 'outcome_blind_selection_required', interpretation: 'descriptive_association_only', disclaimer: 'research only',
      },
    },
    negative: {
      cases: 12,
      fraction: 0.6,
      outcome_feedback: {
        cohort_size: 12,
        cases_with_outcomes: 9,
        outcome_coverage: 0.75,
        outcomes: [{ outcome_type: 'recurrence', observations: 9, known_binary_observations: 9, events: 2, non_events: 7, unknown_or_nonbinary: 0, event_proportion: 0.2222, missingness: 0, value_distribution: {} }],
        research_confidence: 'moderate', selection_boundary: 'outcome_blind_selection_required', interpretation: 'descriptive_association_only', disclaimer: 'research only',
      },
    },
    small_sample_warning: true,
    analysis_type: 'descriptive_cohort_stratification',
    causal_inference: false,
    disclaimer: 'research only',
  },
  evidence_conflict: {
    total: 3, counts: { supporting: 2, conflicting: 1 }, weighted_support: 8, weighted_conflict: 4,
    agreement_ratio: 0.6667, conflict_severity: 'moderate', source_diversity: 3, sources: ['A', 'B', 'C'],
    supports: [], opposes: [], unresolved_reasons: ['both_supporting_and_conflicting_evidence_present'],
    consensus_method: 'context', majority_vote_only: false,
  },
  hypotheses: [hypothesis], trace: [], research_only: true as const, clinical_use: false as const, disclaimer: 'research only',
}

describe('PTCResearchDepthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getResearchDepthPacket.mockResolvedValue(packet)
    mocks.listResearchHypotheses.mockResolvedValue({ count: 1, items: [hypothesis] })
    mocks.listResearchEvents.mockResolvedValue({ count: 1, events: [{
      id: 'event-1', event_key: 'event-1', event_type: 'hypothesis_generated', gene_symbol: 'BRAF',
      observed_at: '2026-08-10T00:00:00', date_semantics: 'generated_at', source_type: 'research_loop', provenance: {}, payload: {},
    }] })
    mocks.runResearchDepthLoop.mockResolvedValue({
      run_id: 'run-1', run_key: 'research-run:BRAF:1', input_fingerprint: 'abcdef1234567890', reused: false,
      trace: [], result_summary: {}, hypotheses: [hypothesis], research_only: true, clinical_use: false,
    })
  })

  it('shows research-only cohort, conflict, hypothesis, and digital-thread outputs', async () => {
    render(<PTCResearchDepthPage />)
    expect(await screen.findByText('PTC 研究深度工作台')).toBeInTheDocument()
    await waitFor(() => expect(mocks.getResearchDepthPacket).toHaveBeenCalledWith('BRAF', 'p.V600E'))
    expect(screen.getByText('Cohort stratification')).toBeInTheDocument()
    expect(screen.getByText('Evidence conflict')).toBeInTheDocument()
    expect(screen.getByText(hypothesis.claim)).toBeInTheDocument()
    expect(screen.getByText('hypothesis_generated')).toBeInTheDocument()
    expect(screen.getByText(/不是預後、因果推論、診斷或治療建議/)).toBeInTheDocument()
  })

  it('runs and persists the controlled research loop', async () => {
    render(<PTCResearchDepthPage />)
    await screen.findByText('PTC 研究深度工作台')
    fireEvent.click(screen.getByRole('button', { name: 'Run research loop' }))
    await waitFor(() => expect(mocks.runResearchDepthLoop).toHaveBeenCalledWith('BRAF', 'p.V600E'))
    expect(await screen.findByText(/Run persisted/)).toBeInTheDocument()
  })
})
