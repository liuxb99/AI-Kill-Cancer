import { apiRequest } from './client'

export interface PTCAssistantCitation {
  evidence_key: string
  source: string
  title?: string
  summary?: string
  level?: string
  direction?: string
  publication_id?: string
  url?: string
  figures: Array<{ id?: string; label?: string; caption?: string; image_url?: string }>
  tables: Array<{ id?: string; label?: string; caption?: string; headers?: string[]; rows?: string[][] }>
  pmcid?: string
}

export interface PTCAssistantResponse {
  case_id: string
  question: string
  intent: string
  selected_gene?: string
  answer: string
  case_facts: {
    source_dataset: string
    pathologic_stage?: string
    tnm: Array<string | null>
    vital_status?: string
    genes: string[]
    variants: Array<{ variant_id: string; gene: string; protein_change?: string; classification?: string }>
    outcomes: Array<{ type: string; value?: string }>
  }
  pathway: Record<string, unknown>
  therapies: Array<{ therapy_key: string; name: string; approval_status?: string; mechanism?: string; source: string; url?: string }>
  evidence: PTCAssistantCitation[]
  trials: Array<{ nct_id: string; title: string; status?: string; phases: string[]; url?: string }>
  actions: Array<{ type: string; label: string; gene?: string; url?: string; nct_id?: string }>
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export function askPTCAssistant(caseId: string, question: string, gene?: string | null): Promise<PTCAssistantResponse> {
  return apiRequest('/ptc-assistant/ask', {
    method: 'POST',
    body: JSON.stringify({ case_id: caseId, question, gene: gene || null }),
  })
}
