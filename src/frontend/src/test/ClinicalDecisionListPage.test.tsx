import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  listRecentDatabasePatients: vi.fn(),
  getDatabasePatient: vi.fn(),
  fetchClinicalDecisionsByPatientId: vi.fn(),
  navigate: vi.fn(),
}))

vi.mock('../api/databasePatients', () => ({
  listRecentDatabasePatients: mocks.listRecentDatabasePatients,
  getDatabasePatient: mocks.getDatabasePatient,
  patientDisplayLabel: (patient: { patient_id: string; display_name?: string }) =>
    patient.display_name ? `${patient.patient_id} · ${patient.display_name}` : patient.patient_id,
}))

vi.mock('../api/clinical_decision', () => ({
  fetchClinicalDecisionsByPatientId: mocks.fetchClinicalDecisionsByPatientId,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mocks.navigate }
})

import ClinicalDecisionListPage from '../pages/ClinicalDecisionListPage'

const patient = { patient_id: 'P-12345', display_name: '測試患者' }
const decision = {
  decision_id: 'dec-001',
  patient_id: 'P-12345',
  decision_type: 'treatment_selection',
  confidence: 'high',
  created_at: '2025-06-18T12:00:00Z',
}

function renderPage(initialEntry = '/clinical-decision') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/clinical-decision" element={<ClinicalDecisionListPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/clinical-decision')
  mocks.listRecentDatabasePatients.mockResolvedValue({ items: [patient], total: 1, skip: 0, limit: 100 })
  mocks.getDatabasePatient.mockResolvedValue(patient)
  mocks.fetchClinicalDecisionsByPatientId.mockResolvedValue({ decisions: [decision], total: 1 })
})

describe('ClinicalDecisionListPage', () => {
  it('renders the title and the dual-mode selector', async () => {
    renderPage()
    expect(screen.getByText('臨床決策列表')).toBeInTheDocument()
    expect(screen.getByText('最近 100 筆')).toBeInTheDocument()
    expect(screen.getByText('進階精準查詢')).toBeInTheDocument()
    expect(await screen.findByText('P-12345 · 測試患者')).toBeInTheDocument()
  })

  it('loads the first recent patient into the shared result area', async () => {
    renderPage()
    expect(await screen.findByText('treatment_selection')).toBeInTheDocument()
    expect(mocks.listRecentDatabasePatients).toHaveBeenCalledWith(100)
    expect(mocks.fetchClinicalDecisionsByPatientId).toHaveBeenCalledWith('P-12345')
    expect(screen.getByText('共 1 筆', { exact: false })).toBeInTheDocument()
  })

  it('switches to advanced mode and queries a full Patient ID', async () => {
    const user = userEvent.setup()
    const advancedPatient = { patient_id: 'P-ADVANCED', display_name: '進階患者' }
    mocks.getDatabasePatient.mockResolvedValueOnce(advancedPatient)
    mocks.fetchClinicalDecisionsByPatientId.mockResolvedValueOnce({
      decisions: [{ ...decision, patient_id: 'P-ADVANCED', decision_id: 'dec-advanced' }],
      total: 1,
    })

    renderPage()
    await screen.findByText('P-12345 · 測試患者')
    await user.click(screen.getByText('進階精準查詢'))
    const input = screen.getByPlaceholderText('輸入完整 UUID Patient ID')
    await user.type(input, 'P-ADVANCED')
    await user.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(mocks.getDatabasePatient).toHaveBeenCalledWith('P-ADVANCED'))
    await waitFor(() => expect(mocks.fetchClinicalDecisionsByPatientId).toHaveBeenCalledWith('P-ADVANCED'))
    expect(await screen.findByText('P-ADVANCED 的決策')).toBeInTheDocument()
  })

  it('restores a deep-linked patientId through the same advanced path', async () => {
    const deepPatient = { patient_id: 'P-DEEP', display_name: '深連結患者' }
    mocks.listRecentDatabasePatients.mockResolvedValueOnce({ items: [], total: 0, skip: 0, limit: 100 })
    mocks.getDatabasePatient.mockResolvedValueOnce(deepPatient)
    mocks.fetchClinicalDecisionsByPatientId.mockResolvedValueOnce({ decisions: [{ ...decision, patient_id: 'P-DEEP' }], total: 1 })
    window.history.replaceState({}, '', '/clinical-decision?patientId=P-DEEP')

    renderPage('/clinical-decision?patientId=P-DEEP')

    await waitFor(() => expect(mocks.getDatabasePatient).toHaveBeenCalledWith('P-DEEP'))
    expect(await screen.findByText('P-DEEP 的決策')).toBeInTheDocument()
  })

  it('shows a shared empty state', async () => {
    mocks.fetchClinicalDecisionsByPatientId.mockResolvedValueOnce({ decisions: [], total: 0 })
    renderPage()
    expect(await screen.findByText('所選患者目前沒有臨床決策記錄。')).toBeInTheDocument()
  })

  it('shows API errors in an alert', async () => {
    mocks.fetchClinicalDecisionsByPatientId.mockRejectedValueOnce(new Error('Network error'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('錯誤：Network error')
  })

  it('navigates to a decision detail page', async () => {
    const user = userEvent.setup()
    renderPage()
    const detail = await screen.findByText('查看詳情 →')
    await user.click(detail)
    expect(mocks.navigate).toHaveBeenCalledWith('/clinical-decision/dec-001')
  })

  it('keeps the route and navigation label registered', async () => {
    const fs = await import('fs')
    const appTsx = fs.readFileSync('./src/App.tsx', 'utf-8')
    expect(appTsx).toContain('<Route path="/clinical-decision"')
    expect(appTsx).toContain("label: '臨床決策'")
  })
})
