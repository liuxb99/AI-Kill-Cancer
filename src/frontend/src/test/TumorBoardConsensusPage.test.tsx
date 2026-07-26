/**
 * Tests for TumorBoardConsensusPage (Phase 3C Frontend).
 *
 * Covers:
 * - Route registration in App.tsx
 * - Page rendering (loading, error, empty, success states)
 * - UI elements (status, score, final recommendation, supporting rationale,
 *   dissenting opinions, unresolved questions, required follow-up,
 *   specialist opinions, trace summary)
 * - API request path correctness
 * - Navigation menu includes tumor-board link
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// ─── Mock fetch globally ──────────────────────────────────────────────────────

const mockFetch = vi.fn()
const MOCK_CONSENSUS_ID = 'cons-001'

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', mockFetch)
})

afterEach(() => {
  cleanup()
})

// ─── Helper: render with router ──────────────────────────────────────────────

function renderPage(consensusId: string = MOCK_CONSENSUS_ID) {
  return render(
    <MemoryRouter initialEntries={[`/tumor-board/${consensusId}`]}>
      <Routes>
        <Route path="/tumor-board/:id" element={<TumorBoardConsensusPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// Import AFTER mocks are set up
import TumorBoardConsensusPage from '../pages/TumorBoardConsensusPage'

// ─── Sample API Response ──────────────────────────────────────────────────────

function createMockResponse(overrides: Record<string, any> = {}) {
  return {
    consensus_id: 'cons-001',
    patient_id: 'P-12345',
    clinical_decision_id: 'dec-abc',
    recommendation_id: 'rec-abc',
    consensus_status: 'unanimous',
    consensus_score: 0.92,
    final_recommendation: 'Continue with Osimertinib 80mg daily',
    supporting_rationale: 'Based on molecular profiling and NCCN guidelines.',
    dissenting_opinions: ['Dr. Smith suggests considering chemotherapy first.'],
    unresolved_questions: ['Long-term cardiac toxicity needs further evaluation.'],
    required_follow_up: ['Re-evaluate after 3 months', 'Echocardiogram in 6 weeks'],
    participating_specialties: ['medical_oncology', 'surgical_oncology'],
    specialist_opinions: [
      {
        specialty: 'medical_oncology',
        position: 'support',
        confidence: 'high',
        rationale: 'Matches standard of care',
      },
      {
        specialty: 'surgical_oncology',
        position: 'support',
        confidence: 'medium',
        rationale: 'Surgery not contraindicated',
      },
    ],
    trace_id: 'Consensus reached after 3 rounds of discussion.',
    created_at: '2025-06-18T12:00:00Z',
    updated_at: '2025-06-18T14:30:00Z',
    ...overrides,
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TumorBoardConsensusPage — Route Registration', () => {
  it('route is registered in App.tsx at /tumor-board/:id', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('/tumor-board/:id')
    expect(appTsx).toContain('TumorBoardConsensusPage')
    expect(appTsx).toContain('<Route path="/tumor-board/:id"')
  })

  it('route is registered in App.tsx at /tumor-board (list page)', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('/tumor-board')
    expect(appTsx).toContain('TumorBoardConsensusListPage')
  })
})

describe('TumorBoardConsensusPage — Rendering', () => {
  it('renders the page title', () => {
    renderPage()
    expect(screen.getByText('腫瘤委員會共識')).toBeInTheDocument()
  })

  it('renders the back button', () => {
    renderPage()
    const backBtn = screen.getByText('←')
    expect(backBtn).toBeInTheDocument()
    expect(backBtn.tagName).toBe('BUTTON')
  })
})

describe('TumorBoardConsensusPage — States', () => {
  it('shows loading state initially', () => {
    // Return a promise that never resolves to keep loading visible
    mockFetch.mockReturnValueOnce(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('正在載入共識資料，請稍候…')).toBeInTheDocument()
    // Loading spinner should be present — look for the SVG spinner
    const spinner = document.querySelector('svg.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('hides loading state after data loads', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.queryByText('正在載入共識資料，請稍候…')).not.toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })
    expect(screen.getByText(/錯誤：/)).toBeInTheDocument()
  })

  it('shows 404 message when API returns 404', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not Found' }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/找不到此共識記錄/)).toBeInTheDocument()
    })
  })

  it('shows HTTP error detail on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Invalid consensus ID' }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Invalid consensus ID/)).toBeInTheDocument()
    })
  })

  it('shows error when consensus ID is missing from URL', async () => {
    // Render directly inside MemoryRouter without Routes matching,
    // so useParams returns {} and id is undefined.
    render(
      <MemoryRouter initialEntries={['/tumor-board/']}>
        <TumorBoardConsensusPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('缺少共識 ID')).toBeInTheDocument()
    })
  })

  it('shows empty state when consensus is null after loading', async () => {
    // Simulate API returning null
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => null,
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('無共識資料')).toBeInTheDocument()
    })
  })
})

describe('TumorBoardConsensusPage — API Request', () => {
  it('sends correct API request on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage('cons-specific')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tumor-board-consensus/cons-specific')
    expect(options.method).toBe('GET')
    // API client sets Content-Type even for GET requests
    expect(options.headers['Content-Type']).toBe('application/json')
  })
})

describe('TumorBoardConsensusPage — UI Elements', () => {
  it('shows consensus status and score', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('共識狀態（Status）')).toBeInTheDocument()
    })
    expect(screen.getByText('一致通過')).toBeInTheDocument()
    expect(screen.getByText('共識分數（Consensus Score）')).toBeInTheDocument()
    expect(screen.getByText('0.92')).toBeInTheDocument()
  })

  it('shows final recommendation', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('最終建議（Final Recommendation）')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Continue with Osimertinib 80mg daily'),
    ).toBeInTheDocument()
  })

  it('shows supporting rationale', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('支持理由（Supporting Rationale）')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Based on molecular profiling and NCCN guidelines.'),
    ).toBeInTheDocument()
  })

  it('shows dissenting opinions', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('異議意見（Dissenting Opinions）')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Dr. Smith suggests considering chemotherapy first.'),
    ).toBeInTheDocument()
  })

  it('shows unresolved questions', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('未解決問題（Unresolved Questions）')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Long-term cardiac toxicity needs further evaluation.'),
    ).toBeInTheDocument()
  })

  it('shows required follow-up items', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('需追蹤事項（Required Follow-up）')).toBeInTheDocument()
    })
    expect(screen.getByText('Re-evaluate after 3 months')).toBeInTheDocument()
    expect(screen.getByText('Echocardiogram in 6 weeks')).toBeInTheDocument()
  })

  it('shows specialist opinions table', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('專科意見（Specialist Opinions）')).toBeInTheDocument()
    })

    // Table headers
    expect(screen.getByText('專科')).toBeInTheDocument()
    expect(screen.getByText('立場')).toBeInTheDocument()
    expect(screen.getByText('信心度')).toBeInTheDocument()
    expect(screen.getByText('理由')).toBeInTheDocument()

    // First row data
    expect(screen.getByText('medical_oncology')).toBeInTheDocument()
    expect(screen.getByText('support')).toBeInTheDocument()

    // Second row data
    expect(screen.getByText('surgical_oncology')).toBeInTheDocument()
  })

  it('shows trace summary', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('推理軌跡摘要（Trace Summary）')).toBeInTheDocument()
    })
    expect(
      screen.getByText('Consensus reached after 3 rounds of discussion.'),
    ).toBeInTheDocument()
  })

  it('shows patient ID and clinical decision ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('患者 ID')).toBeInTheDocument()
    })
    expect(screen.getByText('P-12345')).toBeInTheDocument()
    expect(screen.getByText('臨床決策 ID')).toBeInTheDocument()
    expect(screen.getByText('dec-abc')).toBeInTheDocument()
  })

  it('shows empty placeholders when optional fields are missing', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () =>
        createMockResponse({
          consensus_status: '',
          consensus_score: null,
          final_recommendation: null,
          supporting_rationale: null,
          dissenting_opinions: [],
          unresolved_questions: [],
          required_follow_up: [],
          specialist_opinions: [],
          trace_id: null,
          clinical_decision_id: null,
          patient_id: null,
        }),
    })

    renderPage()

    await waitFor(() => {
      // Default labels when values are empty
      expect(screen.getByText('無建議')).toBeInTheDocument()
      expect(screen.getByText('無說明')).toBeInTheDocument()
    })
    expect(screen.getByText('無異議意見')).toBeInTheDocument()
    expect(screen.getByText('無未解決問題')).toBeInTheDocument()
    expect(screen.getByText('無需追蹤事項')).toBeInTheDocument()
    expect(screen.getByText('無專科意見')).toBeInTheDocument()
    expect(screen.getByText('無推理軌跡')).toBeInTheDocument()
  })

  it('displays correct status badge color for unanimous', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ consensus_status: 'unanimous' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('一致通過')
      expect(badge.className).toContain('text-green-600')
      expect(badge.className).toContain('bg-green-50')
    })
  })

  it('displays correct status badge color for majority_consensus', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ consensus_status: 'majority_consensus' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('多數共識')
      expect(badge.className).toContain('text-amber-600')
      expect(badge.className).toContain('bg-amber-50')
    })
  })

  it('displays correct status badge color for split_decision', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ consensus_status: 'split_decision' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('意見分歧')
      expect(badge.className).toContain('text-orange-600')
      expect(badge.className).toContain('bg-orange-50')
    })
  })

  it('displays consensus ID and created_at in header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      // consensus_id is truncated to 12 chars + …
      expect(screen.getByText(/cons-001/)).toBeInTheDocument()
      // Created date in localized format
      expect(screen.getByText(/2025/)).toBeInTheDocument()
    })
  })

  it('renders consensus detail section label', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('共識詳情')).toBeInTheDocument()
    })
  })
})

describe('TumorBoardConsensusPage — Navigation', () => {
  it('navigation menu contains 腫瘤委員會 link', async () => {
    // We check App.tsx for the nav link registration
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('腫瘤委員會')
    expect(appTsx).toContain('/tumor-board')
    expect(appTsx).toContain("label: '腫瘤委員會'")
  })
})
