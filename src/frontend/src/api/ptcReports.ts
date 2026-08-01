import { apiRequest, apiUrl, withQuery } from './client'

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
    variants?: Array<{ variant_id: string; gene: string; protein_change?: string; classification?: string }>
  }
  pathway: { pathway?: string; protein_domain?: string; downstream?: string[] }
  therapies: Array<{ therapy_key: string; name: string; approval_status?: string; mechanism?: string; source?: string; url?: string }>
  evidence: Array<{ evidence_key: string; source: string; title?: string; summary?: string; level?: string; url?: string; figures?: unknown[]; tables?: unknown[] }>
  trials: Array<{ nct_id: string; title: string; status?: string; url?: string }>
  assets: { figures: number; tables: number }
  trace: Array<{ step: number; name: string; records: number }>
  limitations: string[]
}

function reportPath(caseId: string, format: 'json' | 'html', gene?: string, question?: string): string {
  return withQuery(`/ptc-reports/case/${encodeURIComponent(caseId)}/${format}`, { gene, question })
}

export function getPTCResearchReport(caseId: string, gene?: string, question?: string): Promise<PTCResearchReport> {
  return apiRequest(reportPath(caseId, 'json', gene, question))
}

export function getPTCResearchReportHtmlUrl(caseId: string, gene?: string, question?: string): string {
  return apiUrl(reportPath(caseId, 'html', gene, question))
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
