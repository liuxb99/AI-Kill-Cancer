import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import PTCTimelinePage from '../pages/PTCTimelinePage'

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
      case_id: 'TCGA-TIMELINE-001',
      source_dataset: 'TCGA-THCA',
      source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma',
      pathologic_stage: 'Stage I',
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
      outcomes: [],
    }],
  }),
}))

vi.mock('../api/ptcTimeline', () => ({
  getPTCCaseTimeline: vi.fn().mockResolvedValue({
    case_id: 'TCGA-TIMELINE-001',
    selected_gene: 'BRAF',
    genes: ['BRAF'],
    count: 3,
    events: [
      {
        event_type: 'evidence_ingested', title: 'BRAF evidence', subtitle: 'PubMed · A',
        timestamp: '2026-08-01T10:00:00', date_semantics: 'retrieved_at', gene: 'BRAF', source: 'PubMed',
        payload: {}, actions: [{ type: 'open_literature', label: 'Open publication assets' }],
      },
      {
        event_type: 'variant_ingested', title: 'BRAF p.V600E', subtitle: 'Missense_Mutation',
        timestamp: '2026-07-31T10:00:00', date_semantics: 'ingested_at', gene: 'BRAF', source: 'TCGA-THCA',
        payload: {}, actions: [{ type: 'open_protein', label: 'Open BRAF protein 3D' }],
      },
      {
        event_type: 'outcome_recorded', title: 'vital_status', subtitle: 'Alive',
        timestamp: '2026-07-01T10:00:00', date_semantics: 'observed_at', source: 'TCGA-THCA',
        payload: {}, actions: [],
      },
    ],
    summary: { by_type: { evidence_ingested: 1, variant_ingested: 1, outcome_recorded: 1 } },
    trace: [{ step: 1, name: 'load_case_variants_outcomes', records: 3 }],
    disclaimer: 'Research Digital Thread only.',
  }),
}))

describe('PTCTimelinePage', () => {
  it('renders timeline semantics and opens protein 3D', async () => {
    render(<MemoryRouter><PTCTimelinePage /></MemoryRouter>)
    expect(await screen.findByDisplayValue('TCGA-TIMELINE-001')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('基因筛选'), { target: { value: 'BRAF' } })
    fireEvent.click(screen.getByRole('button', { name: '生成 Digital Thread' }))

    expect(await screen.findByText('BRAF evidence')).toBeInTheDocument()
    expect(screen.getByText('retrieved_at')).toBeInTheDocument()
    expect(screen.getByText('observed_at')).toBeInTheDocument()
    expect(screen.getByText('Research Digital Thread only.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Open BRAF protein 3D' }))
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/ptc-3d?case=TCGA-TIMELINE-001&gene=BRAF&view=protein'))
  })
})
