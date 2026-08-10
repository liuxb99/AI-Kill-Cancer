/**
 * Tests for App.tsx routing and navigation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'

const mockFetch = vi.fn()

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

import App from '../App'

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location-probe">{location.pathname}{location.search}</div>
}

function renderAppAt(initialRoute: string) {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <LocationProbe />
      <App />
    </MemoryRouter>,
  )
}

describe('App — Route: /tumor-board', () => {
  it('renders TumorBoardConsensusListPage at /tumor-board', async () => {
    renderAppAt('/tumor-board')
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
    expect(screen.getByText('腫瘤委員會共識')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('共識詳情')).toBeInTheDocument())
    expect(screen.getByText('Test recommendation')).toBeInTheDocument()
  })

  it('shows 404 error for invalid consensus ID', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: 'Not Found' }) })
    renderAppAt('/tumor-board/invalid-id')
    await waitFor(() => expect(screen.getByText(/找不到此共識記錄/)).toBeInTheDocument())
  })
})

describe('App — Route: /clinical-decision', () => {
  it('renders ClinicalDecisionListPage at /clinical-decision', async () => {
    renderAppAt('/clinical-decision')
    expect(screen.getByText('臨床決策列表')).toBeInTheDocument()
  })

  it('renders ClinicalDecisionPage at /clinical-decision/:id', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        decision_id: 'dec-001', patient_id: 'P-12345', decision_type: 'treatment_selection',
        reason: 'Test reason', evidence_summary: null, confidence: 'high', alternatives: [],
        contraindications: [], recommendation_id: 'rec-001', created_at: '2025-06-18T12:00:00Z', trace_id: 'trace-001',
      }),
    })
    renderAppAt('/clinical-decision/dec-001')
    expect(screen.getAllByText('臨床決策').length).toBeGreaterThanOrEqual(1)
    await waitFor(() => expect(screen.getByText('決策詳情')).toBeInTheDocument())
    expect(screen.getByText('Test reason')).toBeInTheDocument()
  })
})

describe('App — Navigation Bar', () => {
  it('renders the navigation bar with 腫瘤委員會 link', () => {
    renderAppAt('/tumor-board')
    expect(screen.getByText('腫瘤委員會')).toBeInTheDocument()
    expect(screen.getByText('臨床決策')).toBeInTheDocument()
    expect(screen.getByText('藥物推薦')).toBeInTheDocument()
  })

  it('navigates to /tumor-board when clicking 腫瘤委員會 in navbar', async () => {
    renderAppAt('/clinical-decision')
    await userEvent.click(screen.getByText('腫瘤委員會'))
    await waitFor(() => expect(screen.getByText('腫瘤委員會共識列表')).toBeInTheDocument())
  })

  it('navigates to /clinical-decision when clicking 臨床決策 in navbar', async () => {
    renderAppAt('/tumor-board')
    await userEvent.click(screen.getByText('臨床決策'))
    await waitFor(() => expect(screen.getByText('臨床決策列表')).toBeInTheDocument())
  })

  it('preserves demo_case and synthetic data_mode while navigating between demo-capable routes', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ items: [{
        case_key: 'PTC-DEMO-001', display_name: 'Synthetic BRAF Case', cancer_type: 'Papillary Thyroid Carcinoma',
        stage: 'Stage III', radioiodine_status: 'refractory',
        variant: { gene: 'BRAF', hgvs_p: 'p.Val600Glu', variant_type: 'SNV', driver_status: 'driver' },
        drug: { name: 'Demo Drug', mechanism: 'Synthetic mechanism' },
        evidence: { level: 'A', direction: 'supports', summary: 'Synthetic evidence', synthetic: true },
        publication: { title: 'Synthetic Publication', journal: 'Demo Journal' },
        clinical_trial: { id: 'NCT-DEMO-001', title: 'Synthetic Trial', status: 'RECRUITING' },
      }] }),
    })

    renderAppAt('/ptc-research?demo_case=PTC-DEMO-001&data_mode=synthetic')
    expect(await screen.findByTestId('demo-context-banner')).toBeInTheDocument()

    await userEvent.click(screen.getByText('PTC 工作台'))
    await waitFor(() => expect(screen.getByTestId('location-probe')).toHaveTextContent('/ptc-workbench?demo_case=PTC-DEMO-001&data_mode=synthetic'))
    expect(await screen.findByText('Synthetic Integrated Workbench')).toBeInTheDocument()

    await userEvent.click(screen.getByText('PTC 總控台'))
    await waitFor(() => expect(screen.getByTestId('location-probe')).toHaveTextContent('/ptc-command-center?demo_case=PTC-DEMO-001&data_mode=synthetic'))
    expect(await screen.findByText('Synthetic Command Center')).toBeInTheDocument()

    await userEvent.click(screen.getByText('PTC 病例'))
    await waitFor(() => expect(screen.getByTestId('location-probe')).toHaveTextContent('/ptc-research?demo_case=PTC-DEMO-001&data_mode=synthetic'))
    expect(await screen.findByText('PTC 研究工作台')).toBeInTheDocument()
  })
})