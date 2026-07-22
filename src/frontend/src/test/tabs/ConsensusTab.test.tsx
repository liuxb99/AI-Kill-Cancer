/**
 * Tests for ConsensusTab — multi-agent consensus display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const mockConsensus = {
  agreement: 'high',
  confidence: 'high',
  recommended_option: {
    treatment: '帕博利珠单抗 + 化疗',
    rationale: '多项指南推荐作为一线治疗方案',
    evidence_level: '1A',
  },
  alternative_options: [
    {
      treatment: '纳武利尤单抗 + 伊匹木单抗',
      rationale: '适用于PD-L1高表达患者',
      evidence_level: '1B',
    },
  ],
  conflicts: [
    {
      topic: '化疗方案选择',
      detail: '部分专家倾向于卡铂+培美曲塞，部分偏好顺铂+吉西他滨',
    },
  ],
  unresolved_questions: [
    '是否适合在老年患者中减量使用',
    '最佳治疗持续时间尚未确定',
  ],
  created_at: '2025-06-01T10:30:00.000Z',
  context_hash: 'consensus-hash-001',
}

vi.mock('../../api/workbench', () => ({
  getConsensus: vi.fn(),
}))

import { ConsensusTab } from '../../components/tabs/ConsensusTab'

function renderTab(caseId = 'test-case') {
  return render(<ConsensusTab caseId={caseId} />)
}

describe('ConsensusTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockReturnValue(new Promise(() => {}))
    renderTab()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockResolvedValue(mockConsensus)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('🤝 共识结果')).toBeInTheDocument()
    })

    // Agreement and confidence badges
    expect(screen.getByText('共识度: 高')).toBeInTheDocument()
    expect(screen.getByText('信心度: high')).toBeInTheDocument()

    // Recommended option
    expect(screen.getByText('推荐方案')).toBeInTheDocument()
    expect(screen.getByText('首选')).toBeInTheDocument()
    expect(screen.getByText('帕博利珠单抗 + 化疗')).toBeInTheDocument()

    // Alternative options
    expect(screen.getByText('替代方案')).toBeInTheDocument()
    expect(screen.getByText('备选 1')).toBeInTheDocument()
    expect(screen.getByText('纳武利尤单抗 + 伊匹木单抗')).toBeInTheDocument()

    // Conflicts
    expect(screen.getByText('⚠️ 冲突')).toBeInTheDocument()
    expect(screen.getByText(/化疗方案选择/)).toBeInTheDocument()

    // Unresolved questions
    expect(screen.getByText('❓ 未解决问题')).toBeInTheDocument()
    expect(screen.getByText('是否适合在老年患者中减量使用')).toBeInTheDocument()
    expect(screen.getByText('最佳治疗持续时间尚未确定')).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockRejectedValue(new Error('共识服务连接失败'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('无法加载共识结果')).toBeInTheDocument()
    })
    expect(screen.getByText('共识服务连接失败')).toBeInTheDocument()
  })

  it('renders empty state when data is null', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockResolvedValue(null)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无共识数据')).toBeInTheDocument()
    })
  })

  it('renders empty fallback when all sections are empty', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockResolvedValue({
      agreement: 'none',
      confidence: 'low',
      recommended_option: {},
      alternative_options: [],
      conflicts: [],
      unresolved_questions: [],
      created_at: '',
    })
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('共识数据为空')).toBeInTheDocument()
    })
  })

  it('handles missing optional sections gracefully', async () => {
    const { getConsensus } = await import('../../api/workbench')
    getConsensus.mockResolvedValue({
      agreement: 'moderate',
      confidence: 'moderate',
      recommended_option: { treatment: '观察等待' },
      created_at: '',
    })
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('共识度: 中')).toBeInTheDocument()
    })
    expect(screen.getByText('推荐方案')).toBeInTheDocument()
    expect(screen.getByText('观察等待')).toBeInTheDocument()
  })
})
