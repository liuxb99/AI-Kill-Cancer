import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import PTCTargetingPanel from '../components/PTCTargetingPanel'

vi.mock('../api/ptcTargeting', () => ({
  getPTCTargeting: vi.fn().mockResolvedValue({
    gene: 'BRAF',
    pathway: {
      pathway: 'MAPK / ERK',
      protein_domain: 'Serine/threonine kinase domain',
      domain_range: [457, 717],
      hotspots: { V600E: 600 },
      downstream: ['MEK1/2', 'ERK1/2', 'proliferation'],
      therapy_classes: ['BRAF inhibitor'],
    },
    therapies: [{
      therapy_key: 'openfda:dabrafenib',
      name: 'Dabrafenib',
      therapy_type: 'drug',
      approval_status: 'approved',
      indications: ['BRAF V600E'],
      source_name: 'openFDA',
      matched_targets: [{ gene: 'BRAF', variant: 'V600E' }],
    }],
    evidence: [{
      evidence_key: 'e1',
      source_name: 'CIViC',
      title: 'BRAF V600E evidence',
      evidence_level: 'A',
    }],
    trials: [{
      nct_id: 'NCT00000001',
      brief_title: 'BRAF thyroid cancer trial',
      overall_status: 'RECRUITING',
      phases: ['PHASE2'],
      interventions: [],
    }],
    counts: { therapies: 1, evidence: 1, trials: 1 },
    disclaimer: 'Research only',
  }),
}))

describe('PTCTargetingPanel', () => {
  it('shows pathway, mutation domain, therapy, evidence and trial', async () => {
    render(<PTCTargetingPanel gene="BRAF" proteinChange="p.V600E" />)

    expect(await screen.findByText(/BRAF · MAPK \/ ERK/)).toBeInTheDocument()
    expect(screen.getByText(/p\.V600E · residue 600 · 位于目标结构域/)).toBeInTheDocument()
    expect(screen.getByText('Dabrafenib')).toBeInTheDocument()
    expect(screen.getByText('BRAF V600E evidence')).toBeInTheDocument()
    expect(screen.getByText('NCT00000001')).toBeInTheDocument()
    expect(screen.getByText(/MEK1\/2/)).toBeInTheDocument()
  })
})
