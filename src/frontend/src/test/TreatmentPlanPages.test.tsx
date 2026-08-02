import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import TreatmentPlanListPage from '../pages/TreatmentPlanListPage'

const mocks = vi.hoisted(() => ({
  getDatabasePatient: vi.fn(),
  listRecentDatabasePatients: vi.fn(),
  listTreatmentPlans: vi.fn(),
}))

vi.mock('../api/databasePatients', () => ({
  getDatabasePatient: mocks.getDatabasePatient,
  listRecentDatabasePatients: mocks.listRecentDatabasePatients,
  patientDisplayLabel: (patient: { patient_id: string; display_name?: string | null }) =>
    patient.display_name ? `${patient.patient_id} · ${patient.display_name}` : patient.patient_id,
}))

vi.mock('../api/treatmentPlan', () => ({
  listTreatmentPlans: mocks.listTreatmentPlans,
}))

const patient = {
  patient_id: 'P-TEST-001',
  external_id: 'EXT-001',
  display_name: 'Test Patient',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T00:00:00Z',
}

const plan = {
  plan_id: 'plan-001',
  version: 1,
  patient_id: 'P-TEST-001',
  plan_status: 'draft',
  plan_intent: 'curative',
  is_current: true,
  created_at: '2026-08-01T00:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
  window.history.replaceState({}, '', '/treatment-plans')
  mocks.listRecentDatabasePatients.mockResolvedValue({ items: [patient], total: 1, limit: 100 })
  mocks.getDatabasePatient.mockResolvedValue({ ...patient, patient_id: 'P-ARCHIVE-999' })
  mocks.listTreatmentPlans.mockResolvedValue([])
})

function renderPage() {
  return render(
    <MemoryRouter>
      <TreatmentPlanListPage />
    </MemoryRouter>,
  )
}

describe('TreatmentPlanListPage dual-mode workflow', () => {
  it('loads the latest 100 patients and renders the current empty state', async () => {
    renderPage()

    const selector = await screen.findByRole('combobox', { name: '最近 100 位患者' })
    expect(within(selector).getByRole('option', { name: /P-TEST-001/ })).toBeInTheDocument()
    expect(mocks.listRecentDatabasePatients).toHaveBeenCalledWith(100)
    await waitFor(() => expect(mocks.listTreatmentPlans).toHaveBeenCalledWith('P-TEST-001', 0, 20))
    expect(await screen.findByText('所選患者目前沒有 Treatment Plan。')).toBeInTheDocument()
  })

  it('renders a treatment plan returned for the selected recent patient', async () => {
    mocks.listTreatmentPlans.mockResolvedValue([plan])
    renderPage()

    expect(await screen.findByText('plan-001')).toBeInTheDocument()
    expect(screen.getByText('草稿')).toBeInTheDocument()
    expect(screen.getByText('curative')).toBeInTheDocument()
    expect(screen.getByText('✓ 當前')).toBeInTheDocument()
  })

  it('supports exact full-database patient lookup in advanced mode', async () => {
    renderPage()
    await screen.findByRole('combobox', { name: '最近 100 位患者' })

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    fireEvent.change(screen.getByPlaceholderText('輸入完整 UUID Patient ID'), {
      target: { value: 'P-ARCHIVE-999' },
    })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))

    await waitFor(() => expect(mocks.getDatabasePatient).toHaveBeenCalledWith('P-ARCHIVE-999'))
    await waitFor(() => expect(mocks.listTreatmentPlans).toHaveBeenCalledWith('P-ARCHIVE-999', 0, 20))
    expect(window.location.search).toContain('patientId=P-ARCHIVE-999')
  })

  it('shows the advanced lookup error returned by the API', async () => {
    mocks.getDatabasePatient.mockRejectedValue(new Error('Patient not found'))
    renderPage()
    await screen.findByRole('combobox', { name: '最近 100 位患者' })

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    fireEvent.change(screen.getByPlaceholderText('輸入完整 UUID Patient ID'), {
      target: { value: 'P-MISSING' },
    })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))

    expect(await screen.findByText('Patient not found')).toBeInTheDocument()
  })
})
