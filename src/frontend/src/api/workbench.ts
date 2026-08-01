/** Clinical Workbench API client. */
import { apiRequest, withQuery } from './client'

type JsonRecord = Record<string, any>

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
}

function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  return apiRequest<T>(path, {
    method: opts.method || 'GET',
    headers: opts.headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  })
}

const id = (value: string) => encodeURIComponent(value)

export interface GraphNode { id: string; label: string; node_type: string; color: string; size: number; metadata: Record<string, unknown> }
export interface GraphEdge { source_id: string; target_id: string; label: string; edge_type: string }
export interface KnowledgeGraph { nodes: GraphNode[]; edges: GraphEdge[] }
export interface PatientDemographics { id: string; mrn: string; age: number; sex: string; race: string; ethnicity: string }
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
export interface ActivityEntry { id: string; case_id: string; user_id: string; action: string; entity_type: string; entity_id: string; details: Record<string, unknown>; created_at: string }
export interface ActivityLog { entries: ActivityEntry[]; total: number }
export interface DrugInfo { name: string; drugbank_id: string; mechanism: string; status: string; level: string; match_level: string; confidence: number }
export interface WorkbenchTreatmentRecommendation {
  case_id: string
  recommendations: DrugInfo[]
  alternatives: DrugInfo[]
  contraindications: DrugInfo[]
  evidence_summary: string
  generated_at: string
}
export interface WorkbenchTimeline { events: Array<{ type: string; timestamp: string; description: string; user_id?: string }> }
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
  treatment: WorkbenchTreatmentRecommendation
  activity: ActivityLog
}

export function getKnowledgeGraph(caseId: string): Promise<KnowledgeGraph> { return request(`/workbench/graph/case/${id(caseId)}`) }
export function getVariantKnowledgeGraph(variantId: string): Promise<KnowledgeGraph> { return request(`/workbench/graph/variant/${id(variantId)}`) }
export function getPatientSummary(caseId: string): Promise<PatientSummary> { return request(`/workbench/patient/${id(caseId)}/summary`) }
export function getTimeline(caseId: string): Promise<WorkbenchTimeline> { return request(`/workbench/tumor-board/${id(caseId)}/timeline`) }
export function getActivityLog(caseId: string, limit = 50): Promise<ActivityLog> { return request(withQuery(`/workbench/activity/${id(caseId)}`, { limit })) }
export function getTreatmentRecommendation(caseId: string): Promise<WorkbenchTreatmentRecommendation> { return request(`/workbench/treatment/${id(caseId)}`) }
export function getWorkbenchState(caseId: string): Promise<WorkbenchState> { return request(`/workbench/state/${id(caseId)}`) }
export function createTumorBoardReview(caseId: string): Promise<{ review_id: string; status: string }> { return request(`/workbench/tumor-board/${id(caseId)}/review`, { method: 'POST' }) }
export function addTumorBoardVote(caseId: string, vote: { vote: string; rationale: string }): Promise<{ status: string; review_id: string }> { return request(`/workbench/tumor-board/${id(caseId)}/vote`, { method: 'POST', body: vote }) }
export function addTumorBoardComment(caseId: string, comment: { content: string; comment_type?: string }): Promise<{ status: string; review_id: string }> { return request(`/workbench/tumor-board/${id(caseId)}/comment`, { method: 'POST', body: comment }) }
export function compareCases(caseIds: string[]): Promise<CaseComparisonResult> { return request('/workbench/compare/cases', { method: 'POST', body: caseIds }) }

export interface SpecialistOpinion { specialty: string; position: string; confidence: number; rationale: string; participant_id?: string }
export interface TumorBoardConsensus {
  consensus_id: string
  patient_id: string
  clinical_decision_id: string
  recommendation_id: string
  consensus_status: string
  consensus_score?: number
  final_recommendation?: string
  supporting_rationale?: string
  dissenting_opinions: any[]
  unresolved_questions: string[]
  required_follow_up: string[]
  participating_specialties: string[]
  specialist_opinions: SpecialistOpinion[]
  created_by?: string
  trace_id?: string
  created_at: string
  updated_at: string
}
export type TumorBoardConsensusListResponse = TumorBoardConsensus[]
export interface CreateTumorBoardConsensusRequest { patient_id: string; recommendation_id: string; clinical_decision_id: string; specialist_opinions: SpecialistOpinion[] }
export function createTumorBoardConsensus(data: CreateTumorBoardConsensusRequest): Promise<TumorBoardConsensus> { return request('/tumor-board-consensus', { method: 'POST', body: data }) }
export function getTumorBoardConsensus(consensusId: string): Promise<TumorBoardConsensus> { return request(`/tumor-board-consensus/${id(consensusId)}`) }
export function listTumorBoardConsensus(patientId: string, skip = 0, limit = 20): Promise<TumorBoardConsensusListResponse> { return request(withQuery('/tumor-board-consensus', { patient_id: patientId, skip, limit })) }
export function getTumorBoardConsensusOpinions(consensusId: string): Promise<SpecialistOpinion[]> { return request(`/tumor-board-consensus/${id(consensusId)}/opinions`) }
export function getTumorBoardConsensusTrace(consensusId: string): Promise<any[]> { return request(`/tumor-board-consensus/${id(consensusId)}/trace`) }

export function fetchPatientGraphThread(patientId: string): Promise<unknown> { return request(`/clinical-graph/patient/${id(patientId)}/thread`) }
export function fetchRecommendationExplain(recommendationId: string): Promise<unknown> { return request(`/clinical-graph/recommendation/${id(recommendationId)}/explain`) }
export function fetchConsensusExplain(consensusId: string): Promise<unknown> { return request(`/clinical-graph/consensus/${id(consensusId)}/explain`) }

export interface WorkbenchNote { id: string; case_id: string; user_id: string; content: string; note_type: string; created_at: string }
export function getNotes(caseId: string): Promise<WorkbenchNote[]> { return request(`/workbench/case/${id(caseId)}/notes`) }
export function createNote(caseId: string, content: string, noteType = 'general'): Promise<WorkbenchNote> { return request(`/workbench/case/${id(caseId)}/notes`, { method: 'POST', body: { content, note_type: noteType } }) }
export function updateNote(caseId: string, noteId: string, content: string): Promise<WorkbenchNote> { return request(`/workbench/case/${id(caseId)}/notes/${id(noteId)}`, { method: 'PATCH', body: { content } }) }
export function deleteNote(caseId: string, noteId: string): Promise<{ status: string }> { return request(`/workbench/case/${id(caseId)}/notes/${id(noteId)}`, { method: 'DELETE' }) }

export interface ReasoningMessage { id: string; role: string; content: string; evidence?: Array<{ id: string; summary: string; source: string }>; confidence?: number; references?: string[]; decision_trace?: string[]; created_at: string }
export interface ReasoningSession { id: string; case_id: string; messages: ReasoningMessage[]; created_at: string; updated_at: string }
export function createReasoningSession(caseId: string, question: string): Promise<ReasoningSession> { return request(`/workbench/case/${id(caseId)}/reasoning`, { method: 'POST', body: { question } }) }
export function getReasoningSession(caseId: string, sessionId: string): Promise<ReasoningSession> { return request(`/workbench/case/${id(caseId)}/reasoning/${id(sessionId)}`) }
export function listReasoningSessions(caseId: string): Promise<ReasoningSession[]> { return request(`/workbench/case/${id(caseId)}/reasoning`) }

export interface Attachment { id: string; case_id: string; filename: string; file_type: string; media_type: string; size_bytes: number; uploaded_by: string; upload_status: string; created_at: string }
export function getAttachments(caseId: string): Promise<Attachment[]> { return request(`/workbench/case/${id(caseId)}/attachments`) }

export interface VariantInfo { id: string; gene_symbol: string; hgvs_notation: string; protein_change: string; variant_type: string; clinical_significance: string; vaf: number; pathogenicity: string; evidence_level: string; population_frequency: number; annotation_source: string; created_at: string }
export function getCaseVariants(caseId: string, gene?: string, pathogenicity?: string, page = 1, pageSize = 20): Promise<{ variants: VariantInfo[]; total: number }> {
  return request(withQuery(`/workbench/case/${id(caseId)}/variants`, { page, page_size: pageSize, gene, pathogenicity }))
}

export interface ClinicalContext {
  case_id: string
  patient_id: string
  age: number
  gender: string
  diagnosis: string
  stage: string
  histology: string
  cancer_type: string
  oncotree_code?: string
  biomarkers: JsonRecord[]
  variants: JsonRecord[]
  treatment_history: JsonRecord[]
  current_medications: JsonRecord[]
  allergies: string[]
  ecog_score?: number
  metastatic_sites: string[]
  recurrence_status?: string
  clinical_notes?: string
  context_hash: string
}
export interface EvidenceBundle { items: JsonRecord[]; total_count: number; by_source: JsonRecord; by_gene: JsonRecord; by_drug: JsonRecord; highest_level?: string; conflicts_summary: JsonRecord[]; retrieved_at: string; context_hash?: string }
export interface AgentOpinion { agent_type: string; agent_version: string; summary: string; pros: string[]; cons: string[]; confidence: string; references: JsonRecord[]; context_hash?: string; created_at: string }
export interface ConsensusResult { agreement: string; conflicts: JsonRecord[]; confidence: string; recommended_option: JsonRecord; alternative_options: JsonRecord[]; unresolved_questions: string[]; context_hash?: string; created_at: string }
export interface ClinicalTreatmentRecommendation {
  first_line: JsonRecord
  second_line: JsonRecord
  clinical_trial: JsonRecord
  supporting_evidence: JsonRecord[]
  expected_benefit: JsonRecord
  potential_risk: JsonRecord
  monitoring_plan: JsonRecord
  structured_json: JsonRecord
  markdown: string
  context_hash?: string
  created_at: string
}
export interface DecisionNode { id: string; case_id: string; parent_id?: string; node_type: string; reasoning: string; confidence: string; decision_label: string; timestamp: string }
export function getClinicalContext(caseId: string): Promise<ClinicalContext> { return request(`/clinical/context/${id(caseId)}`) }
export function getClinicalEvidence(caseId: string): Promise<EvidenceBundle> { return request(`/clinical/evidence/${id(caseId)}`) }
export function runCaseAnalysis(caseId: string): Promise<{ context: ClinicalContext; evidence: EvidenceBundle; opinions: AgentOpinion[]; consensus: ConsensusResult; recommendation: ClinicalTreatmentRecommendation }> { return request(`/clinical/analysis/${id(caseId)}`, { method: 'POST' }) }
export function runAgents(caseId: string): Promise<AgentOpinion[]> { return request(`/clinical/agents/${id(caseId)}`, { method: 'POST' }) }
export function getConsensus(caseId: string): Promise<ConsensusResult> { return request(`/clinical/consensus/${id(caseId)}`) }
export function getRecommendation(caseId: string): Promise<ClinicalTreatmentRecommendation> { return request(`/clinical/recommendation/${id(caseId)}`) }
export function getDecisionThread(caseId: string): Promise<DecisionNode[]> { return request(`/clinical/thread/${id(caseId)}`) }
export function getDecisionTree(caseId: string): Promise<DecisionNode[]> { return request(`/clinical/tree/${id(caseId)}`) }
export function getDecisionNode(nodeId: string): Promise<DecisionNode> { return request(`/clinical/node/${id(nodeId)}`) }

/** Backward-compatible alias for consumers of the original workbench result type. */
export type TreatmentRecommendation = WorkbenchTreatmentRecommendation
