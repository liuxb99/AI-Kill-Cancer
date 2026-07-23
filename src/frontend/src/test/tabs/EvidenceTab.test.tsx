/**
 * Tests for EvidenceTab — clinical evidence display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const mockEvidence = {
  items: [
    { id: 'ev-1', source: 'PubMed', gene: 'EGFR', drug: '奥希替尼', evidence_level: 'A', confidence: 'high' },
    { id: 'ev-2', source: '临床试验', gene: 'ALK', drug: '阿来替尼', evidence_level: 'B', confidence: 'moderate' },
  ],
  total_count: 2,
  by_source: { PubMed: 1, 临床试验: 1 },
  by_gene: { EGFR: 1, ALK: 1 },
  by_drug: { 奥希替尼: 1, 阿来替尼: 1 },
  highest_level: 'A',
  conflicts_summary: [],
  retrieved_at: '2025-06-01T10:00:00.000Z',
  context_hash: 'evidence-hash-001',
}

vi.mock('../../api/workbench', () => ({
  getClinicalEvidence: vi.fn(),
}))

import { EvidenceTab } from '../../components/tabs/EvidenceTab'

function renderTab(caseId = 'test-case') {
  return render(<EvidenceTab caseId={caseId} />)
}

describe('EvidenceTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockReturnValue(new Promise(() => {}))
    renderTab()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockResolvedValue(mockEvidence)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('📊 临床证据')).toBeInTheDocument()
    })

    // Summary cards — total_count = 2, source count = 2, so "2" appears twice
    expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('高').length).toBeGreaterThanOrEqual(1) // highest level badge
    // by_source has 2 entries, conflict count is 0, so "0" should appear for conflicts
    expect(screen.getByText('0')).toBeInTheDocument()

    // Source grouping — text appears both in grouping header and detail table
    expect(screen.getAllByText('PubMed').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('临床试验').length).toBeGreaterThanOrEqual(1)

    // Evidence table rows
    expect(screen.getByText('奥希替尼')).toBeInTheDocument()
    expect(screen.getByText('阿来替尼')).toBeInTheDocument()
    expect(screen.getByText('EGFR')).toBeInTheDocument()
    expect(screen.getByText('ALK')).toBeInTheDocument()

    // Context hash
    expect(screen.getByText(/evidence-hash/)).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockRejectedValue(new Error('证据服务不可用'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('无法加载证据数据')).toBeInTheDocument()
    })
    expect(screen.getByText('证据服务不可用')).toBeInTheDocument()
  })

  it('renders empty state when data is null', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockResolvedValue(null)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无临床证据数据')).toBeInTheDocument()
    })
  })

  it('renders empty state when total_count is 0', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockResolvedValue({
      items: [],
      total_count: 0,
      by_source: {},
      by_gene: {},
      by_drug: {},
      conflicts_summary: [],
      retrieved_at: '',
    })
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无临床证据数据')).toBeInTheDocument()
    })
  })

  it('renders conflicts summary when present', async () => {
    const { getClinicalEvidence } = await import('../../api/workbench')
    getClinicalEvidence.mockResolvedValue({
      ...mockEvidence,
      conflicts_summary: [
        { topic: 'EGFR T790M', status: '文献矛盾', detail: '不同研究对T790M突变预后意义有分歧' },
      ],
    })
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('⚠️ 冲突摘要')).toBeInTheDocument()
    })
    expect(screen.getByText(/EGFR T790M/)).toBeInTheDocument()
    expect(screen.getByText(/文献矛盾/)).toBeInTheDocument()
  })
})
