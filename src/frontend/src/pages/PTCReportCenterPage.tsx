import { useEffect, useMemo, useState } from 'react'

import DualModeSelector from '../components/DualModeSelector'
import { getPTCCase } from '../api/ptcResearch'
import {
  downloadPTCReportJson,
  getPTCResearchReport,
  getPTCResearchReportHtmlUrl,
  type PTCResearchReport,
} from '../api/ptcReports'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCReportCenterPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [advancedCase, setAdvancedCase] = useState<PTCLatestCase | null>(null)
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [exactCaseId, setExactCaseId] = useState('')
  const [report, setReport] = useState<PTCResearchReport | null>(null)
  const [loadingCases, setLoadingCases] = useState(true)
  const [advancedLoading, setAdvancedLoading] = useState(false)
  const [loadingReport, setLoadingReport] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getLatestPTCCases(100)
      .then((result) => {
        setCases(result.cases)
        const params = new URLSearchParams(window.location.search)
        const requestedCase = params.get('case')
        const requestedGene = params.get('gene')?.toUpperCase() || ''
        const initial = result.cases.find((item) => item.case_id === requestedCase) || result.cases[0]
        if (initial) {
          setSelectedCaseId(initial.case_id)
          const availableGenes = Array.from(new Set(initial.variants.map((item) => item.gene.toUpperCase()))).sort()
          setGene(availableGenes.includes(requestedGene) ? requestedGene : availableGenes[0] || '')
        }
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '無法載入病例'))
      .finally(() => setLoadingCases(false))
  }, [])

  const selectedCase = useMemo(
    () => advancedCase?.case_id === selectedCaseId ? advancedCase : cases.find((item) => item.case_id === selectedCaseId) || null,
    [advancedCase, cases, selectedCaseId],
  )
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  useEffect(() => {
    if (genes.length && !genes.includes(gene)) setGene(genes[0])
    if (!genes.length) setGene('')
  }, [genes, gene])

  function chooseRecentCase(next: string) {
    setAdvancedCase(null)
    setSelectedCaseId(next)
    setReport(null)
  }

  async function queryExactCase() {
    const normalized = exactCaseId.trim()
    if (!normalized) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const record = await getPTCCase(normalized)
      const converted = record as PTCLatestCase
      setAdvancedCase(converted)
      setSelectedCaseId(converted.case_id)
      setGene(converted.variants[0]?.gene?.toUpperCase() || '')
      setReport(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '資料庫找不到指定病例')
    } finally {
      setAdvancedLoading(false)
    }
  }

  async function generate() {
    if (!selectedCaseId) return
    setLoadingReport(true)
    setError(null)
    try {
      setReport(await getPTCResearchReport(selectedCaseId, gene || undefined, undefined))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法生成報告')
    } finally {
      setLoadingReport(false)
    }
  }

  function openPrintable() {
    if (!selectedCaseId) return
    window.open(getPTCResearchReportHtmlUrl(selectedCaseId, gene || undefined, undefined), '_blank', 'noopener,noreferrer')
  }

  const recentContent = (
    <div className="p-4">
      <label className="text-sm font-medium text-gray-700">
        資料庫最近 100 個研究病例
        <select
          className="mt-1 w-full rounded border px-3 py-2"
          value={advancedCase ? '' : selectedCaseId}
          disabled={loadingCases}
          onChange={(event) => chooseRecentCase(event.target.value)}
        >
          <option value="">請選擇病例</option>
          {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'} · {item.variants.length} variants</option>)}
        </select>
      </label>
    </div>
  )

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">PTC Traceable Research Reports</p>
        <h1 className="text-3xl font-bold text-gray-900">PTC 可追溯研究報告中心</h1>
        <p className="mt-2 max-w-4xl text-gray-600">
          一般模式從最近 100 個去識別化病例中選擇；進階模式可用完整 Case ID 查詢整個資料庫。選中病例後，再選擇病例已有基因生成報告。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
        <DualModeSelector
          title="選擇報告病例"
          description="清單與精準查詢會寫入同一個報告結果區。"
          recentContent={recentContent}
          advancedLabel="完整 Case ID"
          advancedPlaceholder="例如 TCGA-XX-YYYY"
          advancedValue={exactCaseId}
          onAdvancedValueChange={setExactCaseId}
          onAdvancedSubmit={queryExactCase}
          advancedLoading={advancedLoading}
          advancedHelp="進階查詢不受最近 100 筆限制；後端會驗證病例是否存在。"
        />

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded border bg-slate-50 p-3 text-sm">
              <div className="text-xs text-gray-500">目前病例</div>
              <div className="mt-1 font-bold">{selectedCaseId || '尚未選擇'}</div>
              {advancedCase && <div className="mt-1 text-xs font-semibold text-indigo-600">進階精準查詢結果</div>}
            </div>
            <label className="text-sm font-medium text-gray-700">
              病例已有基因
              <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => { setGene(event.target.value); setReport(null) }}>
                <option value="">全部基因</option>
                {genes.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button className="rounded bg-indigo-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!selectedCaseId || loadingReport} onClick={() => void generate()}>
              {loadingReport ? '生成中…' : '生成報告預覽'}
            </button>
            <button className="rounded border border-indigo-300 bg-white px-5 py-2.5 font-semibold text-indigo-700 disabled:opacity-50" disabled={!selectedCaseId} onClick={openPrintable}>
              打開列印版／另存 PDF
            </button>
            <button className="rounded border border-slate-300 bg-white px-5 py-2.5 font-semibold text-slate-700 disabled:opacity-50" disabled={!report} onClick={() => report && downloadPTCReportJson(report)}>
              下載 JSON
            </button>
          </div>
        </section>
      </div>

      {!report && !loadingReport && (
        <section className="mt-6 rounded-xl border border-dashed bg-slate-50 p-12 text-center text-slate-500">
          請從最近 100 筆選擇，或使用完整 Case ID 精準查詢，再生成報告。
        </section>
      )}

      {report && <ReportPreview report={report} />}
    </main>
  )
}

function ReportPreview({ report }: { report: PTCResearchReport }) {
  return (
    <article className="mt-6 space-y-5 rounded-xl border bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">{report.schema_version}</p>
          <h2 className="text-2xl font-bold">{report.case_id}</h2>
          <p className="text-sm text-gray-500">Gene: {report.selected_gene || 'All'} · {new Date(report.generated_at).toLocaleString()}</p>
        </div>
        <div className="flex gap-2 text-sm">
          <span className="rounded bg-violet-50 px-3 py-1 text-violet-700">{report.therapies.length} therapies</span>
          <span className="rounded bg-amber-50 px-3 py-1 text-amber-700">{report.evidence.length} evidence</span>
          <span className="rounded bg-emerald-50 px-3 py-1 text-emerald-700">{report.trials.length} trials</span>
        </div>
      </div>
      <section><h3 className="font-bold">執行摘要</h3><p className="mt-2 leading-7 text-gray-700">{report.executive_summary}</p></section>
      <section>
        <h3 className="font-bold">病例與突變</h3>
        <div className="mt-2 overflow-auto rounded border">
          <table className="w-full text-sm"><thead className="bg-slate-50"><tr><th className="p-2 text-left">Gene</th><th className="p-2 text-left">Variant</th><th className="p-2 text-left">Classification</th></tr></thead>
            <tbody>{(report.case_facts.variants || []).map((item) => <tr key={item.variant_id} className="border-t"><td className="p-2 font-semibold">{item.gene}</td><td className="p-2">{item.protein_change || item.variant_id}</td><td className="p-2">{item.classification || '—'}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
      <section><h3 className="font-bold">分子路徑</h3><p className="mt-2 rounded bg-violet-50 p-3 text-violet-900">{report.pathway.pathway || 'Uncurated'} · {report.pathway.protein_domain || 'Domain unavailable'}</p></section>
      <div className="grid gap-5 xl:grid-cols-3">
        <section><h3 className="font-bold">候選研究治療</h3><div className="mt-2 space-y-2">{report.therapies.map((item) => <div key={item.therapy_key} className="rounded border p-3 text-sm"><strong>{item.name}</strong><div className="text-gray-500">{item.approval_status || item.source || '—'}</div></div>)}</div></section>
        <section><h3 className="font-bold">Evidence</h3><div className="mt-2 space-y-2">{report.evidence.slice(0, 10).map((item) => <div key={item.evidence_key} className="rounded border p-3 text-sm"><strong>{item.title || item.evidence_key}</strong><div className="text-gray-500">{item.source} · {item.level || 'ungraded'}</div></div>)}</div></section>
        <section><h3 className="font-bold">Clinical Trials</h3><div className="mt-2 space-y-2">{report.trials.map((item) => <div key={item.nct_id} className="rounded border p-3 text-sm"><strong>{item.nct_id}</strong><div>{item.title}</div><div className="text-gray-500">{item.status || '—'}</div></div>)}</div></section>
      </div>
      <section><h3 className="font-bold">計算軌跡</h3><div className="mt-2 grid gap-2 md:grid-cols-3">{report.trace.map((item) => <div key={item.step} className="rounded border bg-slate-50 p-3 text-sm"><strong>{item.step}. {item.name}</strong><div className="text-gray-500">{item.records} records</div></div>)}</div></section>
      <section className="rounded border border-amber-200 bg-amber-50 p-4"><h3 className="font-bold text-amber-900">限制</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900/80">{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </article>
  )
}
