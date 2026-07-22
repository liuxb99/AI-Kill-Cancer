/**
 * Tests for RecommendationTab — treatment recommendation display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const mockRecommendation = {
  first_line: {
    regimen: '帕博利珠单抗 + 培美曲塞 + 卡铂',
    cycles: '4-6 周期',
    evidence: 'KEYNOTE-189',
  },
  second_line: {
    regimen: '多西他赛 + 雷莫芦单抗',
    evidence: 'REVEL 试验',
  },
  clinical_trial: {
    trial: 'NCT04258462',
    phase: 'III',
    description: '评估信迪利单抗联合化疗',
  },
  supporting_evidence: [
    { source: 'NCCN指南', version: '2025.v1', recommendation: '首选方案' },
    { source: 'ESMO指南', recommendation: 'I类推荐' },
  ],
  expected_benefit: {
    PFS: '8.8个月',
    OS: '22.0个月',
    ORR: '48.3%',
  },
  potential_risk: {
    grade3_4_events: '中性粒细胞减少(22%)、贫血(17%)',
    immune_related: '免疫性肺炎(3.4%)、甲状腺功能减退(8.5%)',
  },
  monitoring_plan: {
    frequency: '每3周',
    assessments: '血常规、肝肾功能、甲状腺功能、影像学评估每2周期',
  },
  markdown: '## 治疗总结\n\n推荐使用帕博利珠单抗联合化疗方案。\n\n- 请监测免疫相关不良反应\n- 每2周期评估疗效',
  created_at: '2025-06-01T11:00:00.000Z',
  context_hash: 'rec-hash-001',
}

vi.mock('../../api/workbench', () => ({
  getRecommendation: vi.fn(),
}))

import { RecommendationTab } from '../../components/tabs/RecommendationTab'

function renderTab(caseId = 'test-case') {
  return render(<RecommendationTab caseId={caseId} />)
}

describe('RecommendationTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockReturnValue(new Promise(() => {}))
    renderTab()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockResolvedValue(mockRecommendation)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('💊 治疗方案推荐')).toBeInTheDocument()
    })

    // First-line section
    expect(screen.getByText('一线治疗')).toBeInTheDocument()
    expect(screen.getByText('帕博利珠单抗 + 培美曲塞 + 卡铂')).toBeInTheDocument()
    expect(screen.getByText('4-6 周期')).toBeInTheDocument()

    // Second-line section
    expect(screen.getByText('二线治疗')).toBeInTheDocument()
    expect(screen.getByText('多西他赛 + 雷莫芦单抗')).toBeInTheDocument()

    // Clinical trial section
    expect(screen.getByText('临床试验')).toBeInTheDocument()
    expect(screen.getByText('NCT04258462')).toBeInTheDocument()

    // Supporting evidence
    expect(screen.getByText('支持证据')).toBeInTheDocument()
    expect(screen.getByText('NCCN指南')).toBeInTheDocument()
    expect(screen.getByText('ESMO指南')).toBeInTheDocument()

    // Expected benefit
    expect(screen.getByText('预期效益')).toBeInTheDocument()
    expect(screen.getByText('8.8个月')).toBeInTheDocument()
    expect(screen.getByText('22.0个月')).toBeInTheDocument()

    // Potential risk
    expect(screen.getByText('潜在风险')).toBeInTheDocument()
    expect(screen.getByText(/中性粒细胞减少/)).toBeInTheDocument()

    // Monitoring plan
    expect(screen.getByText('监测计划')).toBeInTheDocument()
    expect(screen.getByText('每3周')).toBeInTheDocument()

    // Markdown rendered content
    expect(screen.getByText('完整报告')).toBeInTheDocument()
    expect(screen.getByText(/推荐使用帕博利珠单抗联合化疗方案/)).toBeInTheDocument()

    // Context hash
    expect(screen.getByText(/rec-hash/)).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockRejectedValue(new Error('推荐服务异常'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('⚠ 加载失败')).toBeInTheDocument()
    })
    expect(screen.getByText('推荐服务异常')).toBeInTheDocument()
  })

  it('renders empty state when data is null', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockResolvedValue(null)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无治疗方案数据')).toBeInTheDocument()
    })
  })

  it('renders empty state when no structured content and no markdown', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockResolvedValue({
      first_line: {},
      second_line: {},
      clinical_trial: {},
      supporting_evidence: [],
      expected_benefit: {},
      potential_risk: {},
      monitoring_plan: {},
      markdown: '',
      created_at: '',
    })
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('治疗方案数据为空')).toBeInTheDocument()
    })
  })

  it('includes a refresh button', async () => {
    const { getRecommendation } = await import('../../api/workbench')
    getRecommendation.mockResolvedValue(mockRecommendation)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('刷新')).toBeInTheDocument()
    })
  })
})
