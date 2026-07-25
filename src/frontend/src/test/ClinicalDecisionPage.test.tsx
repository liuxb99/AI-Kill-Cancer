/**
 * Tests for ClinicalDecisionPage (Phase 3B Hardening — H8).
 *
 * Covers:
 * - Route registration in App.tsx
 * - Page rendering (loading, error, empty, success states)
 * - UI elements (decision type, reason, evidence, alternatives, contraindications)
 * - API request path correctness
 * - Navigation menu includes clinical-decision link
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

// ─── Mock fetch globally ──────────────────────────────────────────────────────

const mockFetch = vi.fn()
const MOCK_DECISION_ID = 'dec-001'

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', mockFetch)
})

// ─── Helper: render with router ──────────────────────────────────────────────

function renderPage(decisionId: string = MOCK_DECISION_ID) {
  return render(
    <MemoryRouter initialEntries={[`/clinical-decision/${decisionId}`]}>
      <Routes>
        <Route path="/clinical-decision/:id" element={<ClinicalDecisionPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// Import AFTER mocks are set up
import ClinicalDecisionPage from '../pages/ClinicalDecisionPage'

// ─── Sample API Response ──────────────────────────────────────────────────────

function createMockResponse(overrides: Record<string, any> = {}) {
  return {
    decision_id: 'dec-001',
    patient_id: 'P-12345',
    recommendation_id: 'rec-abc',
    decision_type: 'treatment_selection',
    reason: 'Based on EGFR mutation, Osimertinib is recommended as first-line therapy.',
    evidence_summary: {
      source: 'NCCN Guidelines v3.2025',
      evidence_level: 'Category 1',
      citations: ['NCCN-EGFR-001', 'NCCN-EGFR-002'],
    },
    confidence: 'high',
    alternatives: [
      {
        drug: 'Gefitinib',
        rationale: 'Alternative EGFR TKI',
        evidence_level: 'Category 2A',
      },
    ],
    contraindications: [
      {
        drug: 'Osimertinib',
        condition: 'Severe interstitial lung disease',
        severity: 'absolute',
      },
    ],
    created_at: '2025-06-18T12:00:00Z',
    trace_id: 'trace-xyz-789',
    ...overrides,
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ClinicalDecisionPage — Route Registration', () => {
  it('route is registered in App.tsx at /clinical-decision/:id', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('/clinical-decision/:id')
    expect(appTsx).toContain('ClinicalDecisionPage')
    expect(appTsx).toContain('<Route path="/clinical-decision/:id"')
  })
})

describe('ClinicalDecisionPage — Rendering', () => {
  it('renders the page title', () => {
    renderPage()
    expect(screen.getByText('臨床決策')).toBeInTheDocument()
  })

  it('renders the back button', () => {
    renderPage()
    const backBtn = screen.getByText('←')
    expect(backBtn).toBeInTheDocument()
    expect(backBtn.tagName).toBe('BUTTON')
  })
})

describe('ClinicalDecisionPage — States', () => {
  it('shows loading state initially', () => {
    // Return a promise that never resolves to keep loading visible
    mockFetch.mockReturnValueOnce(new Promise(() => {}))

    renderPage()

    expect(screen.getByText('正在載入臨床決策，請稍候…')).toBeInTheDocument()
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
      expect(screen.queryByText('正在載入臨床決策，請稍候…')).not.toBeInTheDocument()
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

  it('shows HTTP error detail on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Decision not found' }),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Decision not found/)).toBeInTheDocument()
    })
  })

  it('shows error when decision ID is missing from URL', async () => {
    // Render directly inside MemoryRouter without Routes matching,
    // so useParams returns {} and id is undefined.
    render(
      <MemoryRouter initialEntries={['/clinical-decision/']}>
        <ClinicalDecisionPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('缺少決策 ID')).toBeInTheDocument()
    })
  })

  it('shows empty state when decision is null after loading', async () => {
    // Simulate API returning null-equivalent (component sets null on empty)
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => null,
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('無決策資料')).toBeInTheDocument()
    })
  })
})

describe('ClinicalDecisionPage — API Request', () => {
  it('sends correct API request on mount', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage('dec-specific')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/api/v1/clinical-decision/dec-specific')
    expect(options.method).toBe('GET')
    // GET requests should not have Content-Type for body-less requests
    // The API client sets Content-Type regardless; verify it's there
    expect(options.headers['Content-Type']).toBe('application/json')
  })
})

describe('ClinicalDecisionPage — UI Elements', () => {
  it('shows decision type and confidence', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('決策類型')).toBeInTheDocument()
    })
    expect(screen.getByText('treatment_selection')).toBeInTheDocument()
    expect(screen.getByText('信心等級')).toBeInTheDocument()
    expect(screen.getByText('high')).toBeInTheDocument()
  })

  it('shows reason text', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('理由（Reason）')).toBeInTheDocument()
    })
    expect(
      screen.getByText(
        'Based on EGFR mutation, Osimertinib is recommended as first-line therapy.',
      ),
    ).toBeInTheDocument()
  })

  it('shows evidence summary', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('證據摘要（Evidence Summary）')).toBeInTheDocument()
    })
    // Evidence is rendered as JSON in a <pre> block
    expect(screen.getByText(/"NCCN Guidelines v3.2025"/)).toBeInTheDocument()
    expect(screen.getByText(/"Category 1"/)).toBeInTheDocument()
  })

  it('shows alternatives', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('替代方案（Alternatives）')).toBeInTheDocument()
    })
    expect(screen.getByText(/"Gefitinib"/)).toBeInTheDocument()
    expect(screen.getByText(/"Alternative EGFR TKI"/)).toBeInTheDocument()
  })

  it('shows contraindications', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('禁忌症（Contraindications）')).toBeInTheDocument()
    })
    expect(screen.getByText(/"Osimertinib"/)).toBeInTheDocument()
    expect(screen.getByText(/"absolute"/)).toBeInTheDocument()
  })

  it('shows patient ID and recommendation ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Patient ID')).toBeInTheDocument()
    })
    expect(screen.getByText('P-12345')).toBeInTheDocument()
    expect(screen.getByText('Recommendation ID')).toBeInTheDocument()
    expect(screen.getByText('rec-abc')).toBeInTheDocument()
  })

  it('shows empty placeholders when optional fields are missing', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({
        decision_type: '',
        reason: '',
        evidence_summary: null,
        alternatives: [],
        contraindications: [],
        patient_id: '',
        recommendation_id: '',
        confidence: '',
      }),
    })

    renderPage()

    await waitFor(() => {
      // Default placeholders for empty values
      const dashes = screen.getAllByText('—')
      expect(dashes.length).toBeGreaterThanOrEqual(4) // decision_type, patient_id, recommendation_id, confidence
    })
    expect(screen.getByText('無說明')).toBeInTheDocument()
    expect(screen.getByText('無證據摘要')).toBeInTheDocument()
    expect(screen.getByText('無替代方案')).toBeInTheDocument()
    expect(screen.getByText('無禁忌症')).toBeInTheDocument()
  })

  it('displays correct confidence badge color for high confidence', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ confidence: 'high' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('high')
      expect(badge.className).toContain('text-green-600')
      expect(badge.className).toContain('bg-green-50')
    })
  })

  it('displays correct confidence badge color for medium confidence', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ confidence: 'medium' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('medium')
      expect(badge.className).toContain('text-amber-600')
      expect(badge.className).toContain('bg-amber-50')
    })
  })

  it('displays correct confidence badge color for low confidence', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse({ confidence: 'low' }),
    })

    renderPage()

    await waitFor(() => {
      const badge = screen.getByText('low')
      expect(badge.className).toContain('text-red-600')
      expect(badge.className).toContain('bg-red-50')
    })
  })

  it('displays decision ID and trace ID in header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      // decision_id is truncated to 12 chars + …
      expect(screen.getByText(/dec-001/)).toBeInTheDocument()
      expect(screen.getByText(/trace: trace-xyz/)).toBeInTheDocument()
    })
  })

  it('renders decision detail section label', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => createMockResponse(),
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('決策詳情')).toBeInTheDocument()
    })
  })
})

describe('ClinicalDecisionPage — Navigation', () => {
  it('navigation menu contains 臨床決策 link', async () => {
    // We check App.tsx for the nav link registration
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('臨床決策')
    expect(appTsx).toContain('/clinical-decision/sample')
    expect(appTsx).toContain("label: '臨床決策'")
  })
})
