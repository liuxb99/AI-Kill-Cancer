/**
 * Tests for AgentsTab — AI agent opinions display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const mockOpinions = [
  {
    agent_type: 'Oncology Advisor',
    agent_version: '2.1.0',
    summary: '推荐使用帕博利珠单抗作为一线治疗',
    pros: ['已获批用于该适应症', '多项III期临床证实有效', '医保覆盖'],
    cons: ['免疫相关不良反应需监测', '部分患者可能出现耐药'],
    confidence: 'high',
    references: [
      { title: 'KEYNOTE-024 试验结果', citation: 'N Engl J Med 2024' },
    ],
    created_at: '2025-06-01T10:00:00.000Z',
  },
  {
    agent_type: 'Radiology AI',
    agent_version: '1.8.3',
    summary: '影像学评估显示治疗反应良好',
    pros: ['肿瘤直径缩小30%', '无新发病灶'],
    cons: ['淋巴结转移灶变化不明显'],
    confidence: 'moderate',
    references: [],
    created_at: '2025-06-01T09:30:00.000Z',
  },
]

vi.mock('../../api/workbench', () => ({
  runAgents: vi.fn(),
}))

import { AgentsTab } from '../../components/tabs/AgentsTab'

function renderTab(caseId = 'test-case') {
  return render(<AgentsTab caseId={caseId} />)
}

describe('AgentsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockReturnValue(new Promise(() => {}))
    renderTab()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockResolvedValue(mockOpinions)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('🧠 智能体意见')).toBeInTheDocument()
    })

    // Header count
    expect(screen.getByText('共 2 个智能体')).toBeInTheDocument()

    // First agent card
    expect(screen.getByText('Oncology Advisor')).toBeInTheDocument()
    expect(screen.getByText('v2.1.0')).toBeInTheDocument()
    expect(screen.getByText('信心度: 高')).toBeInTheDocument()
    expect(screen.getByText('推荐使用帕博利珠单抗作为一线治疗')).toBeInTheDocument()
    expect(screen.getByText('已获批用于该适应症')).toBeInTheDocument()
    expect(screen.getByText('免疫相关不良反应需监测')).toBeInTheDocument()

    // Pros / Cons headers
    expect(screen.getByText('支持论点')).toBeInTheDocument()
    expect(screen.getByText('反对论点')).toBeInTheDocument()

    // References
    expect(screen.getByText('KEYNOTE-024 试验结果')).toBeInTheDocument()

    // Second agent card
    expect(screen.getByText('Radiology AI')).toBeInTheDocument()
    expect(screen.getByText('v1.8.3')).toBeInTheDocument()
    expect(screen.getByText('影像学评估显示治疗反应良好')).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockRejectedValue(new Error('Agent API 超时'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('无法加载智能体意见')).toBeInTheDocument()
    })
    expect(screen.getByText('Agent API 超时')).toBeInTheDocument()
  })

  it('renders empty state when opinions is null', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockResolvedValue(null)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无智能体意见数据')).toBeInTheDocument()
    })
  })

  it('renders empty state when opinions array is empty', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockResolvedValue([])
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无智能体意见数据')).toBeInTheDocument()
    })
  })

  it('handles agent with empty pros/cons gracefully', async () => {
    const { runAgents } = await import('../../api/workbench')
    runAgents.mockResolvedValue([
      {
        agent_type: 'Minimal Agent',
        agent_version: '1.0.0',
        summary: '简要意见',
        pros: [],
        cons: [],
        confidence: 'low',
        references: [],
        created_at: '2025-06-01T00:00:00.000Z',
      },
    ])
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('Minimal Agent')).toBeInTheDocument()
    })
    expect(screen.getByText('无支持论点')).toBeInTheDocument()
    expect(screen.getByText('无反对论点')).toBeInTheDocument()
  })
})
