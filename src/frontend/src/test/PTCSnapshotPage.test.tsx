import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PTCSnapshotPage from '../pages/PTCSnapshotPage'

const mocks = vi.hoisted(() => ({
  latest: vi.fn(),
  create: vi.fn(),
  verify: vi.fn(),
}))

vi.mock('../api/ptcVisualization', () => ({ getLatestPTCCases: mocks.latest }))
vi.mock('../api/ptcSnapshots', () => ({ createPTCSnapshot: mocks.create, verifyPTCSnapshot: mocks.verify }))

describe('PTCSnapshotPage', () => {
  beforeEach(() => {
    mocks.latest.mockResolvedValue({ count: 1, limit: 100, cases: [{ case_id: 'TCGA-SNAP-001', variants: [{ gene: 'BRAF' }] }] })
    mocks.create.mockResolvedValue({
      schema: 'ptc-research-snapshot-v1',
      generated_at: '2026-08-01T00:00:00Z',
      checksum_algorithm: 'SHA-256',
      checksum_sha256: 'abc123',
      content: { case: { case_id: 'TCGA-SNAP-001' }, selected_gene: 'BRAF', variants: [{}], outcomes: [], therapies: [{}], evidence: [{}], clinical_trials: [{}], import_batches: [], counts: { variants: 1, outcomes: 0, therapies: 1, evidence: 1, clinical_trials: 1, import_batches: 0 } },
      trace: [],
      disclaimer: 'Research reproducibility artifact only.',
    })
    mocks.verify.mockResolvedValue({ valid: true, actual: 'abc123', expected: 'abc123', case_id: 'TCGA-SNAP-001' })
  })

  it('generates and displays a checksum-protected snapshot', async () => {
    render(<PTCSnapshotPage />)
    await screen.findByText('TCGA-SNAP-001')
    fireEvent.change(screen.getByLabelText('基因范围'), { target: { value: 'BRAF' } })
    fireEvent.click(screen.getByRole('button', { name: '生成研究快照' }))
    await waitFor(() => expect(mocks.create).toHaveBeenCalledWith('TCGA-SNAP-001', 'BRAF'))
    expect(await screen.findByText('abc123')).toBeInTheDocument()
    expect(screen.getByText('Research reproducibility artifact only.')).toBeInTheDocument()
  })
})
