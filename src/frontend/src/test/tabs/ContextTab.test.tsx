/**
 * Tests for ContextTab — clinical context overview.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const mockContext = {
  case_id: 'test-case',
  patient_id: 'P001',
  age: 52,
  gender: '女',
  diagnosis: '浸润性导管癌',
  stage: 'IIA',
  histology: '腺癌',
  cancer_type: '乳腺癌',
  oncotree_code: 'BRCA',
  biomarkers: [
    { gene: 'ER', status: '阳性', percentage: 80 },
    { gene: 'PR', status: '阳性', percentage: 60 },
    { gene: 'HER2', status: '阴性' },
  ],
  variants: [
    { gene: 'BRCA1', hgvs: 'c.5266dupC', type: 'frameshift', significance: 'pathogenic' },
    { gene: 'TP53', hgvs: 'c.818G>A', type: 'missense', significance: 'likely_pathogenic' },
  ],
  treatment_history: [
    { treatment: '辅助化疗', start_date: '2024-01', end_date: '2024-06', response: 'CR' },
  ],
  current_medications: [
    { name: '来曲唑', dosage: '2.5mg 每日一次' },
  ],
  allergies: ['青霉素', '磺胺类药物'],
  ecog_score: 0,
  metastatic_sites: [],
  recurrence_status: '初诊',
  clinical_notes: '左乳腺改良根治术后，拟行放疗',
  context_hash: 'abc123def456',
}

vi.mock('../../api/workbench', () => ({
  getClinicalContext: vi.fn(),
}))

import { ContextTab } from '../../components/tabs/ContextTab'

function renderTab(caseId = 'test-case') {
  return render(<ContextTab caseId={caseId} />)
}

describe('ContextTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { getClinicalContext } = await import('../../api/workbench')
    getClinicalContext.mockReturnValue(new Promise(() => {})) // never resolves
    renderTab()
    // LoadingSkeleton renders animate-pulse divs
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { getClinicalContext } = await import('../../api/workbench')
    getClinicalContext.mockResolvedValue(mockContext)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('52 岁')).toBeInTheDocument()
    })
    expect(screen.getByText('女')).toBeInTheDocument()
    expect(screen.getByText('浸润性导管癌')).toBeInTheDocument()
    expect(screen.getByText('乳腺癌')).toBeInTheDocument()
    expect(screen.getByText('IIA')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('初诊')).toBeInTheDocument()

    // Allergies
    expect(screen.getByText('青霉素')).toBeInTheDocument()
    expect(screen.getByText('磺胺类药物')).toBeInTheDocument()

    // Biomarkers
    expect(screen.getByText('ER')).toBeInTheDocument()
    expect(screen.getByText('PR')).toBeInTheDocument()
    expect(screen.getByText('HER2')).toBeInTheDocument()

    // Variants in table
    expect(screen.getByText('BRCA1')).toBeInTheDocument()
    expect(screen.getByText('c.5266dupC')).toBeInTheDocument()
    expect(screen.getByText('TP53')).toBeInTheDocument()

    // Treatment history
    expect(screen.getByText('辅助化疗')).toBeInTheDocument()

    // Current medications
    expect(screen.getByText('来曲唑')).toBeInTheDocument()
    expect(screen.getByText('2.5mg 每日一次')).toBeInTheDocument()

    // Clinical notes
    expect(screen.getByText('左乳腺改良根治术后，拟行放疗')).toBeInTheDocument()

    // Context hash footer
    expect(screen.getByText(/abc123def/)).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { getClinicalContext } = await import('../../api/workbench')
    getClinicalContext.mockRejectedValue(new Error('网络请求失败'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('⚠ 加载失败')).toBeInTheDocument()
    })
    expect(screen.getByText('网络请求失败')).toBeInTheDocument()
  })

  it('renders empty state', async () => {
    const { getClinicalContext } = await import('../../api/workbench')
    getClinicalContext.mockResolvedValue(null)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无临床上下文数据')).toBeInTheDocument()
    })
  })

  it('shows fallback texts for missing fields', async () => {
    const { getClinicalContext } = await import('../../api/workbench')
    getClinicalContext.mockResolvedValue({
      case_id: 'test',
      patient_id: '',
      age: 0,
      gender: '',
      diagnosis: '',
      stage: '',
      histology: '',
      cancer_type: '',
      oncotree_code: '',
      biomarkers: [],
      variants: [],
      treatment_history: [],
      current_medications: [],
      allergies: [],
      ecog_score: null,
      metastatic_sites: [],
      recurrence_status: '',
      context_hash: '',
    })
    renderTab()

    await waitFor(() => {
      // Should show fallback dashes
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(3)
    })
    expect(screen.getByText('无已知过敏')).toBeInTheDocument()
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})
