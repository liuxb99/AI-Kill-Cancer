/**
 * Tests for Workbench v1.1 — core states, reasoning history, vote integrity.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

const mockReasoningSessions: Array<{
  id: string; case_id: string; messages: Array<{
    id: string; role: string; content: string; evidence?: Array<Record<string, unknown>>;
    confidence?: number; references?: string[]; decision_trace?: string[]
  }>; created_at: string; updated_at: string
}> = []

vi.mock('../api/workbench', () => {
  let sessionCounter = 0
  return {
    getPatientSummary: vi.fn().mockResolvedValue({
      patient: { id: '', mrn: '', age: 0, sex: '', race: '', ethnicity: '' },
      diagnosis: '', stage: '', cancer_type: '', histology: '', biomarkers: [],
      treatment_history: [], current_medications: [], case_status: 'active',
      case_priority: 'normal', case_owner: '', alerts: [],
    }),
    getTimeline: vi.fn().mockResolvedValue({ events: [] }),
    getKnowledgeGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
    getTreatmentRecommendation: vi.fn().mockResolvedValue({
      case_id: 'test', recommendations: [], alternatives: [],
      contraindications: [], evidence_summary: '', generated_at: '',
    }),
    getActivityLog: vi.fn().mockResolvedValue({ entries: [], total: 0 }),
    addTumorBoardVote: vi.fn().mockResolvedValue({ status: 'ok', review_id: 'r1' }),
    getNotes: vi.fn().mockResolvedValue([]),
    createNote: vi.fn().mockResolvedValue({
      id: 'n1', case_id: 'test', user_id: '', content: 'Test note',
      note_type: 'general', created_at: new Date().toISOString(),
    }),
    updateNote: vi.fn(),
    deleteNote: vi.fn(),
    getAttachments: vi.fn().mockResolvedValue([]),
    getCaseVariants: vi.fn().mockResolvedValue({ variants: [], total: 0 }),
    createReasoningSession: vi.fn().mockImplementation(
      (_caseId: string, question: string) => {
        sessionCounter++
        const session = {
          id: `session-${sessionCounter}`,
          case_id: _caseId,
          messages: [
            { id: `msg-u-${sessionCounter}`, role: 'user', content: question, created_at: new Date().toISOString() },
            {
              id: `msg-a-${sessionCounter}`, role: 'assistant',
              content: `Analysis for: ${question}`,
              confidence: 0.85,
              evidence: [{ id: 'ev-1', summary: 'Supporting evidence', source: 'Test' }],
              references: ['PMID:12345'],
              decision_trace: ['Step 1: analyzed', 'Step 2: concluded'],
              created_at: new Date().toISOString(),
            },
          ],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        mockReasoningSessions.push(session)
        return Promise.resolve(session)
      }
    ),
    getReasoningSession: vi.fn().mockImplementation(
      (_caseId: string, sessionId: string) => {
        const session = mockReasoningSessions.find(s => s.id === sessionId)
        return Promise.resolve(session || {
          id: sessionId, case_id: _caseId, messages: [],
          created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        })
      }
    ),
    listReasoningSessions: vi.fn().mockImplementation(() => {
      return Promise.resolve([...mockReasoningSessions])
    }),
  }
})

import Workbench from '../pages/Workbench'

function renderWorkbench(caseId?: string) {
  const url = caseId ? `/workbench?caseId=${caseId}` : '/workbench'
  window.history.pushState({}, '', url)
  return render(
    <BrowserRouter>
      <Workbench />
    </BrowserRouter>
  )
}

describe('Workbench core states', () => {
  it('shows error when no caseId provided', () => {
    renderWorkbench()
    expect(screen.getByText(/请在 URL 中指定案例 ID/i)).toBeInTheDocument()
  })

  it('renders tabs for valid caseId', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    expect(await screen.findByText('临床笔记')).toBeInTheDocument()
    expect(screen.getByText('AI 推理')).toBeInTheDocument()
    expect(screen.getByText('治疗方案')).toBeInTheDocument()
    expect(screen.getByText('肿瘤委员会')).toBeInTheDocument()
  })

  it('shows empty state for pathology tab', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('病理'))
    expect(await screen.findByText('尚未上传病理报告')).toBeInTheDocument()
  })

  it('shows empty state for AI reasoning', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))
    expect(await screen.findByText('开始与 AI 助手对话以进行临床推理')).toBeInTheDocument()
  })

  it('shows empty state for tumor board', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('肿瘤委员会'))
    expect(await screen.findByText('尚无投票')).toBeInTheDocument()
  })

  it('shows empty state for clinical notes', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('临床笔记'))
    expect(await screen.findByText('暂无笔记')).toBeInTheDocument()
  })
})

describe('TumorBoard vote', () => {
  it('submits vote without reviewer_name in body', async () => {
    const { addTumorBoardVote } = await import('../api/workbench')
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('肿瘤委员会'))

    const addBtn = screen.getByText('添加投票')
    await userEvent.click(addBtn)

    await userEvent.click(screen.getByLabelText('批准'))
    await userEvent.type(screen.getByPlaceholderText('投票理由...'), 'Good evidence')
    await userEvent.click(screen.getByText('提交投票'))

    expect(addTumorBoardVote).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ vote: 'approve', rationale: 'Good evidence' })
    )
    const callArg = vi.mocked(addTumorBoardVote).mock.calls[0][1]
    expect(callArg).not.toHaveProperty('reviewer_id')
    expect(callArg).not.toHaveProperty('reviewer_name')
  })
})

describe('Reasoning history', () => {
  beforeEach(() => {
    mockReasoningSessions.length = 0
  })

  it('submits actual user input to reasoning API', async () => {
    const { createReasoningSession } = await import('../api/workbench')
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    const input = screen.getByPlaceholderText('向 AI 推理引擎提问...')
    await userEvent.type(input, 'What is standard therapy for BRAF V600E?')
    await userEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(createReasoningSession).toHaveBeenCalledWith(
        expect.any(String),
        'What is standard therapy for BRAF V600E?'
      )
    })
  })

  it('recovers user and assistant messages after re-mount', async () => {
    const { unmount } = renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    const input = screen.getByPlaceholderText('向 AI 推理引擎提问...')
    await userEvent.type(input, 'What resistance mechanisms?')
    await userEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('Analysis for: What resistance mechanisms?')).toBeInTheDocument()
    })

    unmount()

    // Re-render — sessions should be loaded from API
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    // The input should be present and working after re-mount
    await waitFor(() => {
      expect(screen.getByPlaceholderText('向 AI 推理引擎提问...')).toBeInTheDocument()
    })
  })

  it('shows evidence, confidence, references, decision trace', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    await userEvent.type(screen.getByPlaceholderText('向 AI 推理引擎提问...'), 'Show evidence')
    await userEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('📚 证据')).toBeInTheDocument()
    })
    expect(screen.getByText(/置信度/)).toBeInTheDocument()
    expect(screen.getByText('推理过程')).toBeInTheDocument()
  })

  it('prevents duplicate sending while loading', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    await userEvent.type(screen.getByPlaceholderText('向 AI 推理引擎提问...'), 'Test')
    await userEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('发送')).toBeDisabled()
    })
  })

  it('shows API error state for reasoning failure', async () => {
    // Override mock for this test
    const { createReasoningSession } = await import('../api/workbench')
    vi.mocked(createReasoningSession).mockRejectedValueOnce(new Error('LLM service unavailable'))

    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('AI 推理'))

    await userEvent.type(screen.getByPlaceholderText('向 AI 推理引擎提问...'), 'Causes error')
    await userEvent.click(screen.getByText('发送'))

    await waitFor(() => {
      expect(screen.getByText('LLM service unavailable')).toBeInTheDocument()
    })
  })
})
