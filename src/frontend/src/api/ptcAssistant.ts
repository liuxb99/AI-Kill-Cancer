const API_BASE = import.meta.env.VITE_API_URL || ''

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
  therapies: Array<{
    therapy_key: string
    name: string
    approval_status?: string
    mechanism?: string
    source: string
    url?: string
  }>
  evidence: PTCAssistantCitation[]
  trials: Array<{
    nct_id: string
    title: string
    status?: string
    phases: string[]
    url?: string
  }>
  actions: Array<{
    type: string
    label: string
    gene?: string
    url?: string
    nct_id?: string
  }>
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export async function askPTCAssistant(
  caseId: string,
  question: string,
  gene?: string | null,
): Promise<PTCAssistantResponse> {
  const response = await fetch(`${API_BASE}/api/v1/ptc-assistant/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, question, gene: gene || null }),
  })
  if (!response.ok) throw new Error(`PTC research assistant failed: HTTP ${response.status}`)
  return response.json()
}
