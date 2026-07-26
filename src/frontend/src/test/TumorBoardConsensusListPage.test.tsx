/**
 * Tests for TumorBoardConsensusListPage (Phase 3C Frontend).
 *
 * Covers:
 * - Route registration in App.tsx
 * - Page rendering (title, query form)
 * - API call via listTumorBoardConsensus
 * - List display with data
 * - Loading state
 * - Empty state
 * - Error state
 * - Pagination
 * - Navigation to detail page
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// ─── Mock fetch globally ──────────────────────────────────────────────────────

const mockFetch = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', mockFetch)
})

// ─── Mock useNavigate ─────────────────────────────────────────────────────────

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// ─── Helper: render with router ──────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/tumor-board']}>
      <Routes>
        <Route path="/tumor-board" element={<TumorBoardConsensusListPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// Import AFTER mocks are set up
import TumorBoardConsensusListPage from '../pages/TumorBoardConsensusListPage'

// ─── Sample API Response ──────────────────────────────────────────────────────

function createMockConsensus(overrides: Record<string, any> = {}) {
  return {
    consensus_id: 'cons-001',
    patient_id: 'P-12345',
    consensus_status: 'unanimous',
    consensus_score: 0.92,
    participating_specialties: ['medical_oncology'],
    recommendation_id: 'rec-abc',
    created_at: '2025-06-18T12:00:00Z',
    ...overrides,
  }
}

function createMockListResponse(items: any[] = [createMockConsensus()]) {
  return items
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TumorBoardConsensusListPage — Route Registration', () => {
  it('route is registered in App.tsx at /tumor-board', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('/tumor-board')
    expect(appTsx).toContain('TumorBoardConsensusListPage')
    expect(appTsx).toContain('<Route path="/tumor-board"')
  })
})

describe('TumorBoardConsensusListPage — Rendering', () => {
  it('renders the page title', () => {
    renderPage()
    expect(screen.getByText('腫瘤委員會共識列表')).toBeInTheDocument()
  })

  it('renders the back button', () => {
    renderPage()
    const backBtn = screen.getByText('←')
    expect(backBtn).toBeInTheDocument()
    expect(backBtn.tagName).toBe('BUTTON')
  })

  it('renders the query form with patient ID input and submit button', () => {
    renderPage()
    expect(screen.getByPlaceholderText('請輸入患者 ID 進行查詢')).toBeInTheDocument()
    expect(screen.getByText('查詢')).toBeInTheDocument()
  })
})

describe('TumorBoardConsensusListPage — States', () => {
  it('shows loading state during API call', async () => {
    // Return a promise that never resolves to keep loading visible
    mockFetch.mockReturnValueOnce(new Promise(() => {}))

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-TEST')
    await userEvent.click(screen.getByText('查詢'))

    expect(await screen.findByText('查詢中…')).toBeInTheDocument()
    // Loading spinner should be present
    const spinner = document.querySelector('svg.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('hides loading state after data loads', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse(),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-LOAD')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.queryByText('查詢中…')).not.toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-ERR')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })
    expect(screen.getByText(/錯誤：/)).toBeInTheDocument()
  })

  it('shows HTTP error detail on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Invalid patient ID' }),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-BAD')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText(/Invalid patient ID/)).toBeInTheDocument()
    })
  })

  it('shows validation error when patient ID is empty', async () => {
    renderPage()
    await userEvent.click(screen.getByText('查詢'))
    expect(screen.getByText('請輸入患者 ID')).toBeInTheDocument()
  })

  it('shows empty state when API returns empty list', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse([]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-EMPTY')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('查無共識記錄')).toBeInTheDocument()
    })
    expect(screen.getByText('請確認患者 ID 是否正確')).toBeInTheDocument()
  })
})

describe('TumorBoardConsensusListPage — API Call', () => {
  it('sends correct API request on submit', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse(),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-TEST-API')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/tumor-board-consensus?patient_id=P-TEST-API&skip=0&limit=20')
    expect(options.method).toBe('GET')
    expect(options.headers['Content-Type']).toBe('application/json')
  })
})

describe('TumorBoardConsensusListPage — List Display', () => {
  it('renders consensus table with correct data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () =>
        createMockListResponse([
          createMockConsensus({
            consensus_id: 'cons-001',
            consensus_status: 'unanimous',
            consensus_score: 0.92,
            participating_specialties: ['medical_oncology'],
            created_at: '2025-06-18T12:00:00Z',
          }),
          createMockConsensus({
            consensus_id: 'cons-002',
            consensus_status: 'majority_consensus',
            consensus_score: 0.75,
            participating_specialties: ['surgical_oncology', 'radiation_oncology'],
            created_at: '2025-06-19T08:30:00Z',
          }),
        ]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-LIST')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('查詢結果')).toBeInTheDocument()
    })

    // Check table headers
    expect(screen.getByText('狀態')).toBeInTheDocument()
    expect(screen.getByText('共識分數')).toBeInTheDocument()
    expect(screen.getByText('專科領域')).toBeInTheDocument()
    expect(screen.getByText('建立時間')).toBeInTheDocument()
    expect(screen.getByText('操作')).toBeInTheDocument()

    // Check first row data
    expect(screen.getByText('一致通過')).toBeInTheDocument()
    expect(screen.getByText('0.92')).toBeInTheDocument()
    expect(screen.getByText('medical_oncology')).toBeInTheDocument()

    // Check second row data
    expect(screen.getByText('多數共識')).toBeInTheDocument()
    expect(screen.getByText('0.75')).toBeInTheDocument()
    expect(screen.getByText('surgical_oncology, radiation_oncology')).toBeInTheDocument()

    // Check total count
    expect(screen.getByText('共 2 筆')).toBeInTheDocument()

    // Check both "查看詳情 →" buttons exist
    const detailBtns = screen.getAllByText('查看詳情 →')
    expect(detailBtns.length).toBe(2)
  })

  it('renders status labels correctly for various statuses', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () =>
        createMockListResponse([
          createMockConsensus({ consensus_id: 'c1', consensus_status: 'unanimous' }),
          createMockConsensus({ consensus_id: 'c2', consensus_status: 'strong_consensus' }),
          createMockConsensus({ consensus_id: 'c3', consensus_status: 'majority_consensus' }),
          createMockConsensus({ consensus_id: 'c4', consensus_status: 'split_decision' }),
          createMockConsensus({ consensus_id: 'c5', consensus_status: 'insufficient_information' }),
          createMockConsensus({ consensus_id: 'c6', consensus_status: 'deferred' }),
        ]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-STATUS')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('一致通過')).toBeInTheDocument()
    })
    expect(screen.getByText('強共識')).toBeInTheDocument()
    expect(screen.getByText('多數共識')).toBeInTheDocument()
    expect(screen.getByText('意見分歧')).toBeInTheDocument()
    expect(screen.getByText('資訊不足')).toBeInTheDocument()
    expect(screen.getByText('暫緩')).toBeInTheDocument()
  })
})

describe('TumorBoardConsensusListPage — Pagination', () => {
  const PAGE_SIZE = 20
  const PAGE_COUNT = 3
  const TOTAL_ITEMS = PAGE_SIZE * PAGE_COUNT // 60 items

  it('shows pagination controls when there are enough items', async () => {
    const items = Array.from({ length: TOTAL_ITEMS }, (_, i) =>
      createMockConsensus({
        consensus_id: `cons-pg-${String(i).padStart(3, '0')}`,
        consensus_status: 'unanimous',
      }),
    )

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse(items),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-PG')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('查詢結果')).toBeInTheDocument()
    })

    // Pagination controls should be visible
    expect(screen.getByText('← 上一頁')).toBeInTheDocument()
    expect(screen.getByText('下一頁 →')).toBeInTheDocument()
    expect(screen.getByText(/第 1 \/ 3 頁/)).toBeInTheDocument()
  })

  it('does not show pagination when there is only one page', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse([createMockConsensus()]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-ONEPG')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('共 1 筆')).toBeInTheDocument()
    })

    expect(screen.queryByText('← 上一頁')).not.toBeInTheDocument()
    expect(screen.queryByText('下一頁 →')).not.toBeInTheDocument()
  })

  it('navigates to the next page', async () => {
    const items = Array.from({ length: TOTAL_ITEMS }, (_, i) =>
      createMockConsensus({
        consensus_id: `cons-pg-${String(i).padStart(3, '0')}`,
        consensus_status: 'unanimous',
      }),
    )

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse(items),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-NEXT')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('查詢結果')).toBeInTheDocument()
    })

    // Second API call when clicking next page
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse(items.slice(PAGE_SIZE, PAGE_SIZE * 2)),
    })

    await userEvent.click(screen.getByText('下一頁 →'))

    await waitFor(() => {
      // Should fetch the next page with skip=20
      const calls = mockFetch.mock.calls
      const nextPageCall = calls.find(
        (c: any) => typeof c[0] === 'string' && c[0].includes('skip=20'),
      )
      expect(nextPageCall).toBeTruthy()
    })
  })
})

describe('TumorBoardConsensusListPage — Navigation', () => {
  it('navigates to detail page when clicking a consensus row', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse([
        createMockConsensus({ consensus_id: 'cons-nav-001', consensus_status: 'unanimous' }),
      ]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-NAV')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('一致通過')).toBeInTheDocument()
    })

    // Click the row (the tr has cursor-pointer and onClick)
    const row = screen.getByText('一致通過').closest('tr')
    expect(row).not.toBeNull()
    await userEvent.click(row!)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/tumor-board/cons-nav-001')
    })
  })

  it('navigates to detail page when clicking the detail button', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockListResponse([
        createMockConsensus({ consensus_id: 'cons-btn-001', consensus_status: 'unanimous' }),
      ]),
    })

    renderPage()
    const input = screen.getByPlaceholderText('請輸入患者 ID 進行查詢')
    await userEvent.type(input, 'P-BTN')
    await userEvent.click(screen.getByText('查詢'))

    await waitFor(() => {
      expect(screen.getByText('一致通過')).toBeInTheDocument()
    })

    // Click the "查看詳情 →" button
    const detailBtn = screen.getByText('查看詳情 →')
    await userEvent.click(detailBtn)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/tumor-board/cons-btn-001')
    })
  })

  it('renders navigation link in App.tsx navbar', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('腫瘤委員會')
    expect(appTsx).toContain('/tumor-board')
    expect(appTsx).toContain("label: '腫瘤委員會'")
  })
})
