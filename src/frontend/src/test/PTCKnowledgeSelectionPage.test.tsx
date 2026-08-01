import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PTCKnowledgePage from '../pages/PTCKnowledgePage'

const mocks = vi.hoisted(() => ({
  getLatestPTCCases: vi.fn(),
  getPTCGeneKnowledge: vi.fn(),
  listPTCTherapies: vi.fn(),
  listPTCTrials: vi.fn(),
  listPTCEvidence: vi.fn(),
  syncPTCClinicalTrials: vi.fn(),
  syncPTCOpenFDA: vi.fn(),
}))

vi.mock('../api/ptcVisualization', () => ({ getLatestPTCCases: mocks.getLatestPTCCases }))
vi.mock('../api/ptcResearch', () => ({
  getPTCGeneKnowledge: mocks.getPTCGeneKnowledge,
  listPTCTherapies: mocks.listPTCTherapies,
  listPTCTrials: mocks.listPTCTrials,
  listPTCEvidence: mocks.listPTCEvidence,
  syncPTCClinicalTrials: mocks.syncPTCClinicalTrials,
  syncPTCOpenFDA: mocks.syncPTCOpenFDA,
}))

describe('PTCKnowledgePage dual-mode workflow', () => {
  beforeEach(() => {
    mocks.getLatestPTCCases.mockResolvedValue({
      count: 1,
      limit: 100,
      cases: [{ case_id: 'TCGA-KNOW-001', pathologic_stage: 'Stage I', variants: [{ gene: 'BRAF' }] }],
    })
    mocks.listPTCTherapies.mockResolvedValue([{ therapy_key: 't1', name: 'Dabrafenib', therapy_type: 'drug', indications: [], warnings: [], source_name: 'openFDA', source_record_id: '1' }])
    mocks.listPTCTrials.mockResolvedValue([])
    mocks.listPTCEvidence.mockResolvedValue([])
    mocks.getPTCGeneKnowledge.mockResolvedValue({ gene: 'BRAF', therapies: [], trials: [], evidence: [] })
    mocks.syncPTCClinicalTrials.mockResolvedValue({ status: 'ok', records: 1 })
    mocks.syncPTCOpenFDA.mockResolvedValue({ status: 'ok', records: 5 })
  })

  it('supports latest-100 selection and advanced exact query', async () => {
    render(<PTCKnowledgePage />)

    expect(await screen.findByDisplayValue('TCGA-KNOW-001')).toBeInTheDocument()
    expect(screen.getByDisplayValue('BRAF')).toBeInTheDocument()
    expect(mocks.getLatestPTCCases).toHaveBeenCalledWith(100)

    fireEvent.click(screen.getByRole('button', { name: '展示所選基因資料' }))
    await waitFor(() => expect(mocks.getPTCGeneKnowledge).toHaveBeenCalledWith('BRAF'))

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    const textbox = screen.getByPlaceholderText(/BRAF、dabrafenib/)
    fireEvent.change(textbox, { target: { value: 'BRAF' } })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))
    await waitFor(() => expect(mocks.getPTCGeneKnowledge).toHaveBeenLastCalledWith('BRAF'))
  })

  it('syncs only the fixed openFDA research drug set', async () => {
    render(<PTCKnowledgePage />)
    await screen.findByText('Dabrafenib')
    fireEvent.click(screen.getByRole('button', { name: '同步固定藥物集合' }))
    await waitFor(() => expect(mocks.syncPTCOpenFDA).toHaveBeenCalledWith([
      'dabrafenib', 'selpercatinib', 'larotrectinib', 'entrectinib', 'trametinib',
    ]))
  })
})
