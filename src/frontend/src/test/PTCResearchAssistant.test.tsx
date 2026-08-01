import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PTCResearchAssistant from '../components/PTCResearchAssistant'

const onOpenGene = vi.fn()

vi.mock('../api/ptcAssistant', () => ({
  askPTCAssistant: vi.fn().mockResolvedValue({
    case_id: 'TCGA-ASSIST-001',
    question: '为什么关注 BRAF V600E？',
    intent: 'overview',
    selected_gene: 'BRAF',
    answer: 'This de-identified research case contains BRAF p.V600E and linked evidence.',
    case_facts: {
      source_dataset: 'TCGA-THCA',
      pathologic_stage: 'Stage I',
      tnm: ['T1', 'N0', 'M0'],
      vital_status: 'Alive',
      genes: ['BRAF'],
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
      outcomes: [],
    },
    pathway: { pathway: 'MAPK / ERK' },
    therapies: [{
      therapy_key: 'openfda:dabrafenib',
      name: 'Dabrafenib',
      approval_status: 'FDA label available',
      source: 'openFDA',
    }],
    evidence: [{
      evidence_key: 'e1',
      source: 'PubMed',
      title: 'BRAF V600E PTC study',
      summary: 'Evidence summary',
      level: 'published_literature',
      publication_id: '123',
      url: 'https://pubmed.ncbi.nlm.nih.gov/123/',
      figures: [{ id: 'fig1', caption: 'BRAF response' }],
      tables: [{ id: 'tbl1', headers: ['Variant'], rows: [['V600E']] }],
      pmcid: 'PMC123',
    }],
    trials: [{
      nct_id: 'NCT00000001',
      title: 'BRAF thyroid cancer trial',
      status: 'RECRUITING',
      phases: ['PHASE2'],
      url: 'https://clinicaltrials.gov/study/NCT00000001',
    }],
    actions: [
      { type: 'open_3d', label: 'Open BRAF protein 3D', gene: 'BRAF' },
      { type: 'open_literature', label: 'Open BRAF figures and tables', gene: 'BRAF' },
    ],
    trace: [
      { step: 1, name: 'resolve_case', records: 1 },
      { step: 6, name: 'compose_auditable_answer', records: 1 },
    ],
    disclaimer: 'For research and education only; not medical advice.',
  }),
}))

describe('PTCResearchAssistant', () => {
  it('runs a selected preset topic and shows auditable evidence', async () => {
    render(<PTCResearchAssistant caseId="TCGA-ASSIST-001" gene="BRAF" onOpenGene={onOpenGene} />)

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '为什么这个病例要关注当前突变？' }))

    expect(await screen.findByText(/This de-identified research case contains BRAF/)).toBeInTheDocument()
    expect(screen.getByText('Dabrafenib')).toBeInTheDocument()
    expect(screen.getByText('BRAF V600E PTC study')).toBeInTheDocument()
    expect(screen.getByText(/compose_auditable_answer/)).toBeInTheDocument()

    fireEvent.click(screen.getByText('BRAF V600E PTC study'))
    expect(await screen.findByText('Evidence summary')).toBeInTheDocument()
    expect(screen.getByText(/1 figures/)).toBeInTheDocument()
    expect(screen.getByText(/1 tables/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Open BRAF protein 3D' }))
    await waitFor(() => expect(onOpenGene).toHaveBeenCalledWith('BRAF'))
  })

  it('disables every preset topic when no case is selected', () => {
    render(<PTCResearchAssistant caseId={null} gene={null} />)
    expect(screen.getByRole('button', { name: '为什么这个病例要关注当前突变？' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '有哪些相关药物与证据？' })).toBeDisabled()
  })
})
