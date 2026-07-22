/**
 * Clinical Workbench API client.
 * Connects to the backend v1 workbench endpoints.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = opts
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string
  label: string
  node_type: string
  color: string
  size: number
  metadata: Record<string, unknown>
}

export interface GraphEdge {
  source_id: string
  target_id: string
  label: string
  edge_type: string
}

export interface KnowledgeGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface PatientDemographics {
  id: string
  mrn: string
  age: number
  sex: string
  race: string
  ethnicity: string
}

export interface PatientSummary {
  patient: PatientDemographics
  diagnosis: string
  stage: string
  cancer_type: string
  histology: string
  biomarkers: string[]
  treatment_history: Array<Record<string, unknown>>
  current_medications: Array<Record<string, unknown>>
  case_status: string
  case_priority: string
  case_owner: string
  alerts: Array<Record<string, unknown>>
}

export interface ActivityEntry {
  id: string
  case_id: string
  user_id: string
  action: string
  entity_type: string
  entity_id: string
  details: Record<string, unknown>
  created_at: string
}

export interface ActivityLog {
  entries: ActivityEntry[]
  total: number
}

export interface DrugInfo {
  name: string
  drugbank_id: string
  mechanism: string
  status: string
  level: string
  match_level: string
  confidence: number
}

export interface TreatmentRecommendation {
  case_id: string
  recommendations: DrugInfo[]
  alternatives: DrugInfo[]
  contraindications: DrugInfo[]
  evidence_summary: string
  generated_at: string
}

export interface WorkbenchTimeline {
  events: Array<{
    type: string
    timestamp: string
    description: string
    user_id?: string
  }>
}

export interface CaseComparisonResult {
  comparison_type: string
  case_ids: string[]
  shared_variants: Array<Record<string, unknown>>
  unique_variants: Record<string, Array<Record<string, unknown>>>
  ranking_differences: Array<Record<string, unknown>>
}

export interface WorkbenchState {
  patient_summary: PatientSummary
  timeline: WorkbenchTimeline
  treatment: TreatmentRecommendation
  activity: ActivityLog
}

// ─── API Functions ───────────────────────────────────────────────────────────

export function getKnowledgeGraph(caseId: string): Promise<KnowledgeGraph> {
  return request(`/workbench/graph/case/${caseId}`)
}

export function getVariantKnowledgeGraph(variantId: string): Promise<KnowledgeGraph> {
  return request(`/workbench/graph/variant/${variantId}`)
}

export function getPatientSummary(caseId: string): Promise<PatientSummary> {
  return request(`/workbench/patient/${caseId}/summary`)
}

export function getTimeline(caseId: string): Promise<WorkbenchTimeline> {
  return request(`/workbench/tumor-board/${caseId}/timeline`)
}

export function getActivityLog(caseId: string, limit = 50): Promise<ActivityLog> {
  return request(`/workbench/activity/${caseId}?limit=${limit}`)
}

export function getTreatmentRecommendation(caseId: string): Promise<TreatmentRecommendation> {
  return request(`/workbench/treatment/${caseId}`)
}

export function getWorkbenchState(caseId: string): Promise<WorkbenchState> {
  return request(`/workbench/state/${caseId}`)
}

export function createTumorBoardReview(caseId: string): Promise<{ review_id: string; status: string }> {
  return request(`/workbench/tumor-board/${caseId}/review`, { method: 'POST' })
}

export function addTumorBoardVote(
  caseId: string,
  vote: { vote: string; rationale: string }
): Promise<{ status: string; review_id: string }> {
  return request(`/workbench/tumor-board/${caseId}/vote`, { method: 'POST', body: vote })
}

export function addTumorBoardComment(
  caseId: string,
  comment: { content: string; comment_type?: string }
): Promise<{ status: string; review_id: string }> {
  return request(`/workbench/tumor-board/${caseId}/comment`, { method: 'POST', body: comment })
}

export function compareCases(caseIds: string[]): Promise<CaseComparisonResult> {
  return request('/workbench/compare/cases', { method: 'POST', body: caseIds })
}

// ─── Notes API ──────────────────────────────────────────────────────────────

export interface WorkbenchNote {
  id: string
  case_id: string
  user_id: string
  content: string
  note_type: string
  created_at: string
}

export function getNotes(caseId: string): Promise<WorkbenchNote[]> {
  return request(`/workbench/case/${caseId}/notes`)
}

export function createNote(caseId: string, content: string, noteType = 'general'): Promise<WorkbenchNote> {
  return request(`/workbench/case/${caseId}/notes`, {
    method: 'POST',
    body: { content, note_type: noteType },
  })
}

export function updateNote(caseId: string, noteId: string, content: string): Promise<WorkbenchNote> {
  return request(`/workbench/case/${caseId}/notes/${noteId}`, {
    method: 'PATCH',
    body: { content },
  })
}

export function deleteNote(caseId: string, noteId: string): Promise<{ status: string }> {
  return request(`/workbench/case/${caseId}/notes/${noteId}`, { method: 'DELETE' })
}

// ─── Reasoning API ──────────────────────────────────────────────────────────

export interface ReasoningMessage {
  id: string
  role: string
  content: string
  evidence?: Array<{ id: string; summary: string; source: string }>
  confidence?: number
  references?: string[]
  decision_trace?: string[]
  created_at: string
}

export interface ReasoningSession {
  id: string
  case_id: string
  messages: ReasoningMessage[]
  created_at: string
  updated_at: string
}

export function createReasoningSession(caseId: string, question: string): Promise<ReasoningSession> {
  return request(`/workbench/case/${caseId}/reasoning`, {
    method: 'POST',
    body: { question },
  })
}

export function getReasoningSession(caseId: string, sessionId: string): Promise<ReasoningSession> {
  return request(`/workbench/case/${caseId}/reasoning/${sessionId}`)
}

export function listReasoningSessions(caseId: string): Promise<ReasoningSession[]> {
  return request(`/workbench/case/${caseId}/reasoning`)
}

// ─── Attachments API ────────────────────────────────────────────────────────

export interface Attachment {
  id: string
  case_id: string
  filename: string
  file_type: string
  media_type: string
  size_bytes: number
  uploaded_by: string
  upload_status: string
  created_at: string
}

export function getAttachments(caseId: string): Promise<Attachment[]> {
  return request(`/workbench/case/${caseId}/attachments`)
}

// ─── Variant API ────────────────────────────────────────────────────────────

export interface VariantInfo {
  id: string
  gene_symbol: string
  hgvs_notation: string
  protein_change: string
  variant_type: string
  clinical_significance: string
  vaf: number
  pathogenicity: string
  evidence_level: string
  population_frequency: number
  annotation_source: string
  created_at: string
}

export function getCaseVariants(caseId: string, gene?: string, pathogenicity?: string, page = 1, pageSize = 20): Promise<{ variants: VariantInfo[]; total: number }> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (gene) params.set('gene', gene)
  if (pathogenicity) params.set('pathogenicity', pathogenicity)
  return request(`/workbench/case/${caseId}/variants?${params}`)
}
