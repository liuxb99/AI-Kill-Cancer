import { apiRequest, withQuery } from './client'

export interface ClinicalDecisionResponse {
  decision_id: string
  patient_id: string
  recommendation_id: string
  decision_type: string
  reason: string
  evidence_summary: Record<string, any> | null
  confidence: string
  alternatives: Record<string, any>[]
  contraindications: Record<string, any>[]
  created_at: string
  trace_id?: string
}

export interface ClinicalDecisionRequest {
  patient_id: string
  recommendation_id: string
  variants: Record<string, any>[]
  context?: Record<string, any>
}

export interface ClinicalDecisionListResponse {
  decisions: ClinicalDecisionResponse[]
  total: number
}

export function fetchClinicalDecisionById(id: string): Promise<ClinicalDecisionResponse> {
  return apiRequest(`/clinical-decision/${encodeURIComponent(id)}`)
}

export function createClinicalDecision(data: ClinicalDecisionRequest): Promise<ClinicalDecisionResponse> {
  return apiRequest('/clinical-decision', { method: 'POST', body: JSON.stringify(data) })
}

export function fetchClinicalDecisionsByPatientId(patientId: string): Promise<ClinicalDecisionListResponse> {
  return apiRequest(withQuery('/clinical-decision', { patient_id: patientId }))
}
