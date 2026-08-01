export interface PTCTimelineAction { type: string; label: string }
export interface PTCTimelineEvent {
  event_type: string
  title: string
  subtitle?: string | null
  timestamp?: string | null
  date_semantics: string
  gene?: string | null
  source?: string | null
  source_url?: string | null
  payload: Record<string, unknown>
  actions: PTCTimelineAction[]
}
export interface PTCTimelineResponse {
  case_id: string
  selected_gene?: string | null
  genes: string[]
  count: number
  events: PTCTimelineEvent[]
  summary: { by_type: Record<string, number>; first_timestamp?: string | null; latest_timestamp?: string | null }
  trace: Array<{ step: number; name: string; records: number }>
  disclaimer: string
}

export async function getPTCCaseTimeline(caseId: string, gene?: string): Promise<PTCTimelineResponse> {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  const query = params.toString()
  const response = await fetch(`/api/v1/ptc-timeline/case/${encodeURIComponent(caseId)}${query ? `?${query}` : ''}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}
