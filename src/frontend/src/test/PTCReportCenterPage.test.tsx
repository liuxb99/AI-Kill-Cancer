import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PTCReportCenterPage from '../pages/PTCReportCenterPage'

const mocks = vi.hoisted(() => ({
  downloadPTCReportJson: vi.fn(),
  getPTCResearchReport: vi.fn(),
}))
const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 1,
    limit: 100,
    cases: [{
      case_id: 'TCGA-REPORT-001',
      source_dataset: 'TCGA-THCA',
      source_project: 'TCGA-THCA',
      disease: 'papillary_thyroid_carcinoma',
      pathologic_stage: 'Stage I',
      variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
      outcomes: [],
    }],
  }),
}))

vi.mock('../api/ptcReports', () => ({
  getPTCResearchReport: mocks.getPTCResearchReport,
  getPTCResearchReportHtmlUrl: vi.fn().mockReturnValue('/api/v1/ptc-reports/case/TCGA-REPORT-001/html?gene=BRAF'),
  downloadPTCReportJson: mocks.downloadPTCReportJson,
}))

const report = {
  schema_version: 'ptc-research-report-v1',
  generated_at: '2026-08-01T06:00:00Z',
  report_type: 'deidentified_public_research',
  case_id: 'TCGA-REPORT-001',
  selected_gene: 'BRAF',
  executive_summary: 'BRAF V600E evidence-grounded summary.',
  case_facts: {
    source_dataset: 'TCGA-THCA',
    pathologic_stage: 'Stage I',
    variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
  },
  pathway: { pathway: 'MAPK / ERK', protein_domain: 'Kinase domain' },
  therapies: [{ therapy_key: 't1', name: 'Dabrafenib', approval_status: 'FDA label available' }],
  evidence: [{ evidence_key: 'e1', source: 'PubMed', title: 'BRAF PTC study', figures: [{}], tables: [{}] }],
  trials: [{ nct_id: 'NCT00000001', title: 'BRAF trial', status: 'RECRUITING' }],
  assets: { figures: 1, tables: 1 },
  trace: [{ step: 1, name: 'resolve_case', records: 1 }],
  limitations: ['Research only'],
}

describe('PTCReportCenterPage', () => {
  beforeEach(() => {
    mocks.getPTCResearchReport.mockReset()
    mocks.getPTCResearchReport.mockResolvedValue(report)
  })

  it('generates a report from database selections without text query input', async () => {
    render(<PTCReportCenterPage />)

    expect(await screen.findByDisplayValue(/TCGA-REPORT-001/)).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '生成报告预览' }))

    expect(await screen.findByText('BRAF V600E evidence-grounded summary.')).toBeInTheDocument()
    expect(mocks.getPTCResearchReport).toHaveBeenCalledWith('TCGA-REPORT-001', 'BRAF', undefined)
    expect(screen.getByText('Dabrafenib')).toBeInTheDocument()
    expect(screen.getByText('BRAF PTC study')).toBeInTheDocument()
    expect(screen.getByText('NCT00000001')).toBeInTheDocument()
    expect(screen.getByText(/resolve_case/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '打开列印版／另存 PDF' }))
    expect(openSpy).toHaveBeenCalledWith(
      '/api/v1/ptc-reports/case/TCGA-REPORT-001/html?gene=BRAF',
      '_blank',
      'noopener,noreferrer',
    )

    fireEvent.click(screen.getByRole('button', { name: '下载 JSON' }))
    await waitFor(() => expect(mocks.downloadPTCReportJson).toHaveBeenCalled())
  })
})
