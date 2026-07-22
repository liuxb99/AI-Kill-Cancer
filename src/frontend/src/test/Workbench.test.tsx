/**
 * Tests for Workbench page components.
 * Covers: error states, loading, empty states, Notes load/save, Tumor Board vote body.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Mock the API module
vi.mock('../api/workbench', () => ({
  getPatientSummary: vi.fn().mockResolvedValue({
    patient: { id: '', mrn: '', age: 0, sex: '', race: '', ethnicity: '' },
    diagnosis: '',
    stage: '',
    cancer_type: '',
    histology: '',
    biomarkers: [],
    treatment_history: [],
    current_medications: [],
    case_status: 'active',
    case_priority: 'normal',
    case_owner: '',
    alerts: [],
  }),
  getTimeline: vi.fn().mockResolvedValue({ events: [] }),
  getKnowledgeGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getTreatmentRecommendation: vi.fn().mockResolvedValue({
    case_id: 'test', recommendations: [], alternatives: [], contraindications: [], evidence_summary: '', generated_at: '',
  }),
  getActivityLog: vi.fn().mockResolvedValue({ entries: [], total: 0 }),
  addTumorBoardVote: vi.fn().mockResolvedValue({ status: 'ok', review_id: 'r1' }),
  getNotes: vi.fn().mockResolvedValue([]),
  createNote: vi.fn().mockResolvedValue({ id: 'n1', case_id: 'test', user_id: '', content: 'New clinical note content', note_type: 'general', created_at: new Date().toISOString() }),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
  getAttachments: vi.fn().mockResolvedValue([]),
  getCaseVariants: vi.fn().mockResolvedValue({ variants: [], total: 0 }),
  createReasoningSession: vi.fn(),
  getReasoningSession: vi.fn(),
  listReasoningSessions: vi.fn().mockResolvedValue([]),
}))

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

describe('Workbench', () => {
  it('shows error when no caseId provided', () => {
    renderWorkbench()
    expect(screen.getByText(/请在 URL 中指定案例 ID/i)).toBeInTheDocument()
  })

  it('renders tabs for valid caseId', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    // Tab labels unique to tab bar (not in sidebar)
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
})

describe('ClinicalNotesPanel', () => {
  it('renders empty state initially', async () => {
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('临床笔记'))
    expect(await screen.findByText('暂无笔记')).toBeInTheDocument()
  })
})

describe('TumorBoardPanel', () => {
  it('submits vote without reviewer_name in body', async () => {
    const { addTumorBoardVote } = await import('../api/workbench')
    renderWorkbench('123e4567-e89b-12d3-a456-426614174000')
    await userEvent.click(await screen.findByText('肿瘤委员会'))

    // Open vote form
    const addBtn = screen.getByText('添加投票')
    await userEvent.click(addBtn)

    // Select approve
    const approveRadio = screen.getByLabelText('批准')
    await userEvent.click(approveRadio)

    // Enter rationale
    const rationaleInput = screen.getByPlaceholderText('投票理由...')
    await userEvent.type(rationaleInput, 'Based on evidence review')

    // Submit
    const submitBtn = screen.getByText('提交投票')
    await userEvent.click(submitBtn)

    // Verify the API was called without reviewer_id/reviewer_name
    expect(addTumorBoardVote).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        vote: 'approve',
        rationale: 'Based on evidence review',
      })
    )
    const callArg = vi.mocked(addTumorBoardVote).mock.calls[0][1]
    expect(callArg).not.toHaveProperty('reviewer_id')
    expect(callArg).not.toHaveProperty('reviewer_name')
  })
})
