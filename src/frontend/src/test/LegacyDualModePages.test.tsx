import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ClinicalDecisionListPage from '../pages/ClinicalDecisionListPage'
import ClinicalGraphPage from '../pages/ClinicalGraphPage'
import RecommendationPage from '../pages/RecommendationPage'
import TreatmentPlanListPage from '../pages/TreatmentPlanListPage'

const mocks = vi.hoisted(() => ({
  listRecentDatabasePatients: vi.fn(),
  getDatabasePatient: vi.fn(),
  fetchClinicalDecisionsByPatientId: vi.fn(),
  listTreatmentPlans: vi.fn(),
  getLatestPTCCases: vi.fn(),
}))

vi.mock('../api/databasePatients', () => ({
  listRecentDatabasePatients: mocks.listRecentDatabasePatients,
  getDatabasePatient: mocks.getDatabasePatient,
  patientDisplayLabel: (item: { patient_id: string }) => item.patient_id,
}))

vi.mock('../api/clinical_decision', () => ({
  fetchClinicalDecisionsByPatientId: mocks.fetchClinicalDecisionsByPatientId,
}))

vi.mock('../api/treatmentPlan', () => ({
  listTreatmentPlans: mocks.listTreatmentPlans,
}))

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: mocks.getLatestPTCCases,
}))

const patient = { patient_id: '11111111-1111-1111-1111-111111111111', external_id: 'P-001' }

beforeEach(() => {
  vi.restoreAllMocks()
  mocks.listRecentDatabasePatients.mockResolvedValue({ items: [patient], total: 1, skip: 0, limit: 100 })
  mocks.getDatabasePatient.mockResolvedValue(patient)
  mocks.fetchClinicalDecisionsByPatientId.mockResolvedValue({
    decisions: [{ decision_id: 'decision-1', patient_id: patient.patient_id, decision_type: 'therapy', confidence: 'high', created_at: '2026-08-01T00:00:00Z' }],
    total: 1,
  })
  mocks.listTreatmentPlans.mockResolvedValue([{ plan_id: 'plan-1', version: 1, plan_status: 'active', plan_intent: 'disease_control', is_current: true, created_at: '2026-08-01T00:00:00Z' }])
  mocks.getLatestPTCCases.mockResolvedValue({
    count: 1,
    limit: 100,
    cases: [{ case_id: 'TCGA-REC-001', pathologic_stage: 'Stage I', variants: [{ gene: 'BRAF', protein_change: 'p.V600E' }] }],
  })
})

describe('legacy dual-mode pages', () => {
  it('loads recent patients and supports precise patient search in clinical decisions', async () => {
    render(<MemoryRouter><ClinicalDecisionListPage /></MemoryRouter>)
    expect(await screen.findByText('therapy')).toBeInTheDocument()
    expect(mocks.listRecentDatabasePatients).toHaveBeenCalledWith(100)

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    fireEvent.change(screen.getByPlaceholderText('輸入完整 UUID Patient ID'), { target: { value: patient.patient_id } })
    fireEvent.click(screen.getByRole('button', { name: '精準查詢' }))
    await waitFor(() => expect(mocks.getDatabasePatient).toHaveBeenCalledWith(patient.patient_id))
  })

  it('loads treatment plans from the selected recent patient', async () => {
    render(<MemoryRouter><TreatmentPlanListPage /></MemoryRouter>)
    expect(await screen.findByText('plan-1')).toBeInTheDocument()
    expect(mocks.listTreatmentPlans).toHaveBeenCalledWith(patient.patient_id, 0, 20)
  })

  it('uses the same-origin graph endpoint for the selected patient', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      patient_id: patient.patient_id,
      entities: [{ id: 'e1', kind: 'Patient', name: 'P-001' }],
      relations: [],
      projection_status: 'ready',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    render(<MemoryRouter><ClinicalGraphPage /></MemoryRouter>)
    expect(await screen.findByText('P-001')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/clinical-graph/patient/${patient.patient_id}/thread`,
      expect.any(Object),
    )
  })

  it('selects a recent PTC case and auto-fills recommendation variants', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      recommendation_id: 'rec-1',
      patient_id: 'TCGA-REC-001',
      recommendations: [],
      trace_id: 'trace-1',
      engine_version: 'v1',
      created_at: '2026-08-01T00:00:00Z',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    render(<MemoryRouter><RecommendationPage /></MemoryRouter>)
    expect(await screen.findByDisplayValue(/BRAF p.V600E/)).toBeInTheDocument()
    expect(mocks.getLatestPTCCases).toHaveBeenCalledWith(100)
    fireEvent.click(screen.getByRole('button', { name: '產生推薦' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/recommendation', expect.any(Object)))
  })
})
