/**
 * Tests for DecisionThreadTab — decision tree display.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const mockNodes = [
  {
    id: 'node-1',
    case_id: 'test-case',
    parent_id: null,
    node_type: 'context_built',
    reasoning: '患者为52岁女性，确诊乳腺癌IIA期，ER+/PR+/HER2-',
    confidence: '0.95',
    decision_label: '初始化上下文',
    timestamp: '2025-06-01T08:00:00.000Z',
  },
  {
    id: 'node-2',
    case_id: 'test-case',
    parent_id: 'node-1',
    node_type: 'evidence_collected',
    reasoning: '收集到 KEYNOTE-522 等临床试验证据',
    confidence: '0.85',
    decision_label: '证据收集完成',
    timestamp: '2025-06-01T08:30:00.000Z',
  },
  {
    id: 'node-3',
    case_id: 'test-case',
    parent_id: 'node-1',
    node_type: 'agent_opinion',
    reasoning: 'Oncology Advisor 推荐帕博利珠单抗方案',
    confidence: '0.72',
    decision_label: '智能体意见汇总',
    timestamp: '2025-06-01T09:00:00.000Z',
  },
  {
    id: 'node-4',
    case_id: 'test-case',
    parent_id: 'node-1',
    node_type: 'consensus_reached',
    reasoning: '各智能体就一线治疗方案达成高共识',
    confidence: '0.88',
    decision_label: '共识达成',
    timestamp: '2025-06-01T09:30:00.000Z',
  },
  {
    id: 'node-5',
    case_id: 'test-case',
    parent_id: 'node-1',
    node_type: 'recommendation_generated',
    reasoning: '生成治疗推荐：帕博利珠单抗 + 培美曲塞 + 卡铂',
    confidence: '0.9',
    decision_label: '推荐方案生成',
    timestamp: '2025-06-01T10:00:00.000Z',
  },
]

vi.mock('../../api/workbench', () => ({
  getDecisionThread: vi.fn(),
}))

import { DecisionThreadTab } from '../../components/tabs/DecisionThreadTab'

function renderTab(caseId = 'test-case') {
  return render(<DecisionThreadTab caseId={caseId} />)
}

describe('DecisionThreadTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockReturnValue(new Promise(() => {}))
    renderTab()
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders data correctly', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockResolvedValue(mockNodes)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('决策线程')).toBeInTheDocument()
    })

    // Header
    expect(screen.getByText('决策线程')).toBeInTheDocument()
    expect(screen.getByText('刷新')).toBeInTheDocument()

    // Node type labels — root node visible by default
    expect(screen.getByText('上下文构建')).toBeInTheDocument()

    // Initially collapsed — child count shown instead of child labels
    expect(screen.getByText('4 个子节点...')).toBeInTheDocument()
  })

  it('renders error state', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockRejectedValue(new Error('决策线程加载失败'))
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('⚠ 加载失败')).toBeInTheDocument()
    })
    expect(screen.getByText('决策线程加载失败')).toBeInTheDocument()
  })

  it('renders empty state when tree is empty', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockResolvedValue([])
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('暂无决策数据')).toBeInTheDocument()
    })
  })

  it('expands nodes on click', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockResolvedValue(mockNodes)
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('上下文构建')).toBeInTheDocument()
    })

    // Click the first node to expand
    const nodeHeader = screen.getByText('上下文构建').closest('div[class*="rounded-r-lg"]')!
    fireEvent.click(nodeHeader)

    // Expanded reasoning should appear
    await waitFor(() => {
      expect(screen.getByText('患者为52岁女性，确诊乳腺癌IIA期，ER+/PR+/HER2-')).toBeInTheDocument()
    })

    // Confidence should be shown
    expect(screen.getByText('95%')).toBeInTheDocument()

    // Node ID snippet
    expect(screen.getByText(/node-1/)).toBeInTheDocument()
  })

  it('renders default node type label for unknown types', async () => {
    const { getDecisionThread } = await import('../../api/workbench')
    getDecisionThread.mockResolvedValue([
      {
        id: 'unknown-node',
        case_id: 'test',
        parent_id: null,
        node_type: 'custom_type',
        reasoning: '自定义节点类型',
        confidence: '0.5',
        decision_label: '自定义',
        timestamp: '2025-06-01T00:00:00.000Z',
      },
    ])
    renderTab()

    await waitFor(() => {
      expect(screen.getByText('custom_type')).toBeInTheDocument()
    })
  })
})
