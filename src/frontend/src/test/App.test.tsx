/**
 * Tests for App.tsx routing and navigation (Phase 3C Frontend).
 *
 * Covers:
 * - /tumor-board route renders TumorBoardConsensusListPage
 * - /tumor-board/:id route renders TumorBoardConsensusPage
 * - Navigation bar has "腫瘤委員會" link
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

// ─── Mock fetch globally ──────────────────────────────────────────────────────

const mockFetch = vi.fn()

// Mock StatusBanner to avoid its health-check fetch consuming mock calls
vi.mock('../components/StatusBanner', () => ({
  default: () => null,
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', mockFetch)
})

afterEach(() => {
  cleanup()
})

// Import AFTER mocks are set up
import App from '../App'

// ─── Helper: render App with a given route ────────────────────────────────────

function renderAppAt(initialRoute: string) {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('App — Route: /tumor-board', () => {
  it('renders TumorBoardConsensusListPage at /tumor-board', async () => {
    renderAppAt('/tumor-board')

    // The list page title should be rendered
    expect(screen.getByText('腫瘤委員會共識列表')).toBeInTheDocument()
  })

  it('renders the query form on the list page', async () => {
    renderAppAt('/tumor-board')

    expect(screen.getByPlaceholderText('請輸入患者 ID 進行查詢')).toBeInTheDocument()
    expect(screen.getByText('查詢')).toBeInTheDocument()
  })
})

describe('App — Route: /tumor-board/:id', () => {
  it('renders TumorBoardConsensusPage at /tumor-board/:id', async () => {
    // The detail page calls fetch on mount; resolve with mock data
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        consensus_id: 'cons-001',
        patient_id: 'P-12345',
        clinical_decision_id: 'dec-abc',
        recommendation_id: 'rec-abc',
        consensus_status: 'unanimous',
        consensus_score: 0.92,
        final_recommendation: 'Test recommendation',
        supporting_rationale: 'Test rationale',
        dissenting_opinions: [],
        unresolved_questions: [],
        required_follow_up: [],
        participating_specialties: [],
        specialist_opinions: [],
        trace_id: 'Test trace',
        created_at: '2025-06-18T12:00:00Z',
        updated_at: '2025-06-18T12:00:00Z',
      }),
    })

    renderAppAt('/tumor-board/cons-001')

    // The detail page title should be rendered
    expect(screen.getByText('腫瘤委員會共識')).toBeInTheDocument()

    // Wait for data to load and verify detail content
    await waitFor(() => {
      expect(screen.getByText('共識詳情')).toBeInTheDocument()
    })
    expect(screen.getByText('Test recommendation')).toBeInTheDocument()
  })

  it('shows 404 error for invalid consensus ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not Found' }),
    })

    renderAppAt('/tumor-board/invalid-id')

    await waitFor(() => {
      expect(screen.getByText(/找不到此共識記錄/)).toBeInTheDocument()
    })
  })
})

describe('App — Route: /clinical-decision (for reference)', () => {
  it('renders ClinicalDecisionListPage at /clinical-decision', async () => {
    renderAppAt('/clinical-decision')

    expect(screen.getByText('臨床決策列表')).toBeInTheDocument()
  })

  it('renders ClinicalDecisionPage at /clinical-decision/:id', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        decision_id: 'dec-001',
        patient_id: 'P-12345',
        decision_type: 'treatment_selection',
        reason: 'Test reason',
        evidence_summary: null,
        confidence: 'high',
        alternatives: [],
        contraindications: [],
        recommendation_id: 'rec-001',
        created_at: '2025-06-18T12:00:00Z',
        trace_id: 'trace-001',
      }),
    })

    renderAppAt('/clinical-decision/dec-001')

    expect(screen.getByText('臨床決策')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('決策詳情')).toBeInTheDocument()
    })
    expect(screen.getByText('Test reason')).toBeInTheDocument()
  })
})

describe('App — Navigation Bar', () => {
  it('renders the navigation bar with 腫瘤委員會 link', () => {
    renderAppAt('/tumor-board')

    // The navbar should contain the nav links
    expect(screen.getByText('腫瘤委員會')).toBeInTheDocument()
    expect(screen.getByText('臨床決策')).toBeInTheDocument()
    expect(screen.getByText('藥物推薦')).toBeInTheDocument()
  })

  it('navigates to /tumor-board when clicking 腫瘤委員會 in navbar', async () => {
    // Start at a different page so the navbar is visible (home page hides it)
    renderAppAt('/clinical-decision')

    // Click on 腫瘤委員會 in the navbar
    await userEvent.click(screen.getByText('腫瘤委員會'))

    // Should now show the TumorBoardConsensusListPage
    await waitFor(() => {
      expect(screen.getByText('腫瘤委員會共識列表')).toBeInTheDocument()
    })
  })

  it('navigates to /clinical-decision when clicking 臨床決策 in navbar', async () => {
    renderAppAt('/tumor-board')

    await userEvent.click(screen.getByText('臨床決策'))

    await waitFor(() => {
      expect(screen.getByText('臨床決策列表')).toBeInTheDocument()
    })
  })
})
