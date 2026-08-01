import { apiRequest, withQuery } from './client'

export interface TreatmentPlanResponse {
  plan_id: string
  version: number
  patient_id: string
  recommendation_id: string
  clinical_decision_id: string
  consensus_id: string
  plan_status: string
  plan_intent: string | null
  treatment_goals: string[]
  summary: string | null
  clinical_rationale: string | null
  phases: Record<string, any>[]
  items: Record<string, any>[]
  monitoring: Record<string, any>[]
  safety_rules: Record<string, any>[]
  alternatives: Record<string, any>[]
  trace: Record<string, any>[]
  is_current: boolean
  previous_plan_id: string | null
  supersedes_plan_id: string | null
  revision_reason: string | null
  created_by: string | null
  approved_by: string | null
  approved_at: string | null
  activated_at: string | null
  review_date?: string | null
  created_at: string
}

export interface TreatmentPlanListItem {
  plan_id: string
  version: number
  patient_id: string
  plan_status: string
  plan_intent: string | null
  is_current: boolean
  created_at: string
}

export interface CreateTreatmentPlanRequest {
  patient_id: string
  recommendation_id: string
  clinical_decision_id: string
  consensus_id: string
  plan_intent: string
  treatment_goals: string[]
  clinical_context: Record<string, any>
  monitoring_requirements?: Record<string, any>[]
}

export interface ReviseTreatmentPlanRequest {
  plan_intent: string
  treatment_goals: string[]
  clinical_context: Record<string, any>
  revision_reason: string
}

export function createTreatmentPlan(data: CreateTreatmentPlanRequest): Promise<TreatmentPlanResponse> {
  return apiRequest('/treatment-plans', { method: 'POST', body: JSON.stringify(data) })
}

export function getTreatmentPlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}`)
}

export function listTreatmentPlans(patientId: string, skip = 0, limit = 20): Promise<TreatmentPlanListItem[]> {
  return apiRequest(withQuery('/treatment-plans', { patient_id: patientId, skip, limit }))
}

export function getPlanVersions(planId: string): Promise<TreatmentPlanResponse[]> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/versions`)
}

export function getPlanTrace(planId: string): Promise<Record<string, any>[]> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/trace`)
}

export function submitPlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/submit`, { method: 'POST' })
}

export function approvePlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/approve`, { method: 'POST' })
}

export function activatePlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/activate`, { method: 'POST' })
}

export function pausePlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/pause`, { method: 'POST' })
}

export function completePlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/complete`, { method: 'POST' })
}

export function cancelPlan(planId: string): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/cancel`, { method: 'POST' })
}

export function revisePlan(planId: string, data: ReviseTreatmentPlanRequest): Promise<TreatmentPlanResponse> {
  return apiRequest(`/treatment-plans/${encodeURIComponent(planId)}/revise`, { method: 'POST', body: JSON.stringify(data) })
}
