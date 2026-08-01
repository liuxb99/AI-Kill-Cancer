import { useEffect, useMemo, useState } from 'react'

import {
  downloadPTCReportJson,
  getPTCResearchReport,
  getPTCResearchReportHtmlUrl,
  type PTCResearchReport,
} from '../api/ptcReports'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCReportCenterPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [question, setQuestion] = useState('')
  const [report, setReport] = useState<PTCResearchReport | null>(null)
  const [loadingCases, setLoadingCases] = useState(true)
  const [loadingReport, setLoadingReport] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getLatestPTCCases(100)
      .then((result) => {
        setCases(result.cases)
        const first = result.cases[0]
        if (first) setSelectedCaseId(first.case_id)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '无法载入病例'))
      .finally(() => setLoadingCases(false))
  }, [])

  const selectedCase = useMemo(
    () => cases.find((item) => item.case_id === selectedCaseId) || null,
    [cases, selectedCaseId],
  )
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  useEffect(() => {
    if (genes.length && !genes.includes(gene)) setGene(genes[0])
    if (!genes.length) setGene('')
  }, [genes, gene])

  async function generate() {
    if (!selectedCaseId) return
    setLoadingReport(true)
    setError(null)
    try {
      setReport(await getPTCResearchReport(selectedCaseId, gene || undefined, question || undefined))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成报告')
    } finally {
      setLoadingReport(false)
    }
  }

  function openPrintable() {
    if (!selectedCaseId) return
    window.open(getPTCResearchReportHtmlUrl(selectedCaseId, gene || undefined, question || undefined), '_blank', 'noopener,noreferrer')
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">PTC Traceable Research Reports</p>
        <h1 className="text-3xl font-bold text-gray-900">PTC 可追溯研究报告中心</h1>
        <p className="mt-2 max-w-4xl text-gray-600">
          从去识别化 TCGA-THCA 病例生成包含突变、蛋白路径、候选研究药物、Evidence、临床试验、PMC 图表与计算轨迹的报告。
          HTML 版本可直接使用浏览器打印或另存 PDF。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="rounded-xl border bg-white p-5 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="text-sm font-medium text-gray-700">
            研究病例
            <select
              className="mt-1 w-full rounded border px-3 py-2"
              value={selectedCaseId}
              disabled={loadingCases}
              onChange={(event) => {
                setSelectedCaseId(event.target.value)
                setReport(null)
              }}
            >
              {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700">
            分子焦点
            <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value)}>
              <option value="">全部基因</option>
              {genes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700 md:col-span-2">
            报告问题／研究重点
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="例如：整理 BRAF V600E 的结构、候选药物、论文图表与临床试验证据"
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="rounded bg-indigo-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!selectedCaseId || loadingReport} onClick={() => void generate()}>
            {loadingReport ? '生成中…' : '生成报告预览'}
          </button>
          <button className="rounded border border-indigo-300 bg-white px-5 py-2.5 font-semibold text-indigo-700 disabled:opacity-50" disabled={!selectedCaseId} onClick={openPrintable}>
            打开列印版／另存 PDF
          </button>
          <button className="rounded border border-slate-300 bg-white px-5 py-2.5 font-semibold text-slate-700 disabled:opacity-50" disabled={!report} onClick={() => report && downloadPTCReportJson(report)}>
            下载 JSON
          </button>
        </div>
      </section>

      {!report && !loadingReport && (
        <section className="mt-6 rounded-xl border border-dashed bg-slate-50 p-12 text-center text-slate-500">
          选择病例与基因后生成报告。当前数据库共有 {cases.length} 个最近病例可选。
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

      <section><h3 className="font-bold">执行摘要</h3><p className="mt-2 leading-7 text-gray-700">{report.executive_summary}</p></section>

      <section>
        <h3 className="font-bold">病例与突变</h3>
        <div className="mt-2 overflow-auto rounded border">
          <table className="w-full text-sm"><thead className="bg-slate-50"><tr><th className="p-2 text-left">Gene</th><th className="p-2 text-left">Variant</th><th className="p-2 text-left">Classification</th></tr></thead>
            <tbody>{(report.case_facts.variants || []).map((item) => <tr key={item.variant_id} className="border-t"><td className="p-2 font-semibold">{item.gene}</td><td className="p-2">{item.protein_change || item.variant_id}</td><td className="p-2">{item.classification || '—'}</td></tr>)}</tbody>
          </table>
        </div>
      </section>

      <section><h3 className="font-bold">分子路径</h3><p className="mt-2 rounded bg-violet-50 p-3 text-violet-900">{report.pathway.pathway || 'Uncurated'} · {report.pathway.protein_domain || 'Domain unavailable'}</p></section>

      <div className="grid gap-5 xl:grid-cols-3">
        <section><h3 className="font-bold">候选研究治疗</h3><div className="mt-2 space-y-2">{report.therapies.map((item) => <div key={item.therapy_key} className="rounded border p-3 text-sm"><strong>{item.name}</strong><div className="text-gray-500">{item.approval_status || item.source || '—'}</div></div>)}</div></section>
        <section><h3 className="font-bold">Evidence</h3><div className="mt-2 space-y-2">{report.evidence.slice(0, 10).map((item) => <div key={item.evidence_key} className="rounded border p-3 text-sm"><strong>{item.title || item.evidence_key}</strong><div className="text-gray-500">{item.source} · {item.level || 'ungraded'}</div><div className="text-xs text-gray-400">{item.figures?.length || 0} figures · {item.tables?.length || 0} tables</div></div>)}</div></section>
        <section><h3 className="font-bold">Clinical Trials</h3><div className="mt-2 space-y-2">{report.trials.map((item) => <div key={item.nct_id} className="rounded border p-3 text-sm"><strong>{item.nct_id}</strong><div>{item.title}</div><div className="text-gray-500">{item.status || '—'}</div></div>)}</div></section>
      </div>

      <section><h3 className="font-bold">计算轨迹</h3><div className="mt-2 grid gap-2 md:grid-cols-3">{report.trace.map((item) => <div key={item.step} className="rounded border bg-slate-50 p-3 text-sm"><strong>{item.step}. {item.name}</strong><div className="text-gray-500">{item.records} records</div></div>)}</div></section>

      <section className="rounded border border-amber-200 bg-amber-50 p-4"><h3 className="font-bold text-amber-900">限制</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900/80">{report.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </article>
  )
}
