const API_BASE = import.meta.env.VITE_API_URL || ''

export interface PTCResearchReport {
  schema_version: string
  generated_at: string
  report_type: string
  case_id: string
  selected_gene?: string
  question?: string
  executive_summary?: string
  case_facts: {
    source_dataset?: string
    pathologic_stage?: string
    vital_status?: string
    genes?: string[]
    variants?: Array<{
      variant_id: string
      gene: string
      protein_change?: string
      classification?: string
    }>
  }
  pathway: {
    pathway?: string
    protein_domain?: string
    downstream?: string[]
  }
  therapies: Array<{
    therapy_key: string
    name: string
    approval_status?: string
    mechanism?: string
    source?: string
    url?: string
  }>
  evidence: Array<{
    evidence_key: string
    source: string
    title?: string
    summary?: string
    level?: string
    url?: string
    figures?: unknown[]
    tables?: unknown[]
  }>
  trials: Array<{
    nct_id: string
    title: string
    status?: string
    url?: string
  }>
  assets: { figures: number; tables: number }
  trace: Array<{ step: number; name: string; records: number }>
  limitations: string[]
}

function queryString(gene?: string, question?: string) {
  const params = new URLSearchParams()
  if (gene) params.set('gene', gene)
  if (question) params.set('question', question)
  const value = params.toString()
  return value ? `?${value}` : ''
}

export async function getPTCResearchReport(caseId: string, gene?: string, question?: string): Promise<PTCResearchReport> {
  const response = await fetch(`${API_BASE}/api/v1/ptc-reports/case/${encodeURIComponent(caseId)}/json${queryString(gene, question)}`)
  if (!response.ok) throw new Error(`无法生成 PTC 研究报告：HTTP ${response.status}`)
  return response.json()
}

export function getPTCResearchReportHtmlUrl(caseId: string, gene?: string, question?: string): string {
  return `${API_BASE}/api/v1/ptc-reports/case/${encodeURIComponent(caseId)}/html${queryString(gene, question)}`
}

export function downloadPTCReportJson(report: PTCResearchReport) {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `ptc-research-report-${report.case_id}${report.selected_gene ? `-${report.selected_gene}` : ''}.json`
  anchor.click()
  URL.revokeObjectURL(url)
}
