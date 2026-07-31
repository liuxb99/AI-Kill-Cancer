import { useEffect, useState } from 'react'

import { listPTCCases, type PTCResearchCase } from '../api/ptcResearch'
import {
  bootstrapPTCHerbs,
  calculatePTCSimilarity,
  generatePTCIntegratedRecommendation,
  getPTCIntegratedDashboard,
  listPTCHerbs,
  listPTCInteractions,
  type PTCDashboard,
  type PTCHerb,
  type PTCIntegratedRecommendation,
  type PTCInteraction,
} from '../api/ptcIntegrated'

export default function PTCIntegratedPage() {
  const [dashboard, setDashboard] = useState<PTCDashboard | null>(null)
  const [cases, setCases] = useState<PTCResearchCase[]>([])
  const [selectedCase, setSelectedCase] = useState('')
  const [herbs, setHerbs] = useState<PTCHerb[]>([])
  const [interactions, setInteractions] = useState<PTCInteraction[]>([])
  const [recommendation, setRecommendation] = useState<PTCIntegratedRecommendation | null>(null)
  const [similar, setSimilar] = useState<Array<Record<string, any>>>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [summary, caseRows, herbRows, interactionRows] = await Promise.all([
        getPTCIntegratedDashboard(),
        listPTCCases(),
        listPTCHerbs(),
        listPTCInteractions(),
      ])
      setDashboard(summary)
      setCases(caseRows)
      setSelectedCase((current) => current || caseRows[0]?.case_id || '')
      setHerbs(herbRows)
      setInteractions(interactionRows)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 整合工作台')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function bootstrap() {
    setError(null)
    setMessage(null)
    try {
      const result = await bootstrapPTCHerbs()
      setMessage(`科學中藥研究種子已建立：${result.herbs_created} herbs / ${result.compounds_created} compounds`)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '建立科學中藥研究種子失敗')
    }
  }

  async function analyse() {
    if (!selectedCase) return
    setLoading(true)
    setError(null)
    try {
      const [rec, similarRows] = await Promise.all([
        generatePTCIntegratedRecommendation(selectedCase),
        calculatePTCSimilarity(selectedCase),
      ])
      setRecommendation(rec)
      setSimilar(similarRows)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PTC 研究分析失敗')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">PTC Research Workbench</p>
        <h1 className="text-3xl font-bold">甲狀腺乳突癌整合研究工作台</h1>
        <p className="mt-2 text-gray-600">
          串聯研究病例、基因變異、藥物、證據、臨床試驗、科學中藥研究與交互作用。輸出僅供研究與臨床決策支援，不構成處方。
        </p>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">{message}</div>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-7">
        <Metric label="病例" value={dashboard?.case_count} />
        <Metric label="變異" value={dashboard?.variant_count} />
        <Metric label="藥物" value={dashboard?.therapy_count} />
        <Metric label="證據" value={dashboard?.evidence_count} />
        <Metric label="試驗" value={dashboard?.trial_count} />
        <Metric label="中藥研究" value={dashboard?.herb_count} />
        <Metric label="交互作用" value={dashboard?.interaction_count} />
      </section>

      <section className="mt-6 rounded-lg border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-72 flex-1 text-sm font-medium">
            選擇研究病例
            <select className="mt-1 w-full rounded border px-3 py-2" value={selectedCase} onChange={(event) => setSelectedCase(event.target.value)}>
              <option value="">尚無病例</option>
              {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'stage unknown'}</option>)}
            </select>
          </label>
          <button className="rounded bg-primary-600 px-4 py-2 text-white" disabled={!selectedCase || loading} onClick={() => void analyse()}>
            產生整合研究分析
          </button>
          <button className="rounded border px-4 py-2" onClick={() => void bootstrap()}>
            建立科學中藥研究種子
          </button>
        </div>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-3">
        <Panel title="高頻基因">
          <div className="space-y-2">
            {dashboard?.top_genes.map((item) => (
              <div key={item.gene} className="flex justify-between rounded border px-3 py-2 text-sm">
                <span className="font-semibold">{item.gene}</span><span>{item.case_count} cases</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title={`科學中藥研究 (${herbs.length})`}>
          {herbs.map((item) => (
            <article key={item.herb_key} className="border-b py-3 last:border-0">
              <div className="font-semibold">{item.chinese_name} <span className="text-xs font-normal text-gray-500">{item.latin_name}</span></div>
              <div className="mt-1 flex flex-wrap gap-1">{item.investigated_genes.map((gene) => <Tag key={gene}>{gene}</Tag>)}</div>
              <p className="mt-2 text-xs text-amber-700">{item.evidence_level} · 不代表已證實治療效果</p>
            </article>
          ))}
          {herbs.length === 0 && <Empty />}
        </Panel>
        <Panel title={`交互作用警告 (${interactions.length})`}>
          {interactions.map((item, index) => (
            <article key={`${item.herb_key}-${item.therapy_key}-${index}`} className="border-b py-3 last:border-0">
              <div className="font-semibold">{item.herb_key}</div>
              <div className="text-sm">↔ {item.therapy_key}</div>
              <div className="mt-1 text-xs text-red-700">{item.severity} · {item.interaction_type}</div>
              {item.recommendation && <p className="mt-2 text-xs text-gray-600">{item.recommendation}</p>}
            </article>
          ))}
          {interactions.length === 0 && <Empty />}
        </Panel>
      </section>

      {recommendation && (
        <section className="mt-6 space-y-6">
          <div className="rounded-lg border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="text-xl font-bold">研究分析：{recommendation.case_id}</h2><p className="text-sm text-gray-500">{recommendation.engine_version}</p></div>
              <div className="rounded bg-indigo-50 px-3 py-2 text-indigo-700">Confidence {Math.round(recommendation.confidence * 100)}%</div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{recommendation.genes.map((gene) => <Tag key={gene}>{gene}</Tag>)}</div>
            <p className="mt-4 text-sm text-gray-700">{recommendation.explanation}</p>
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <ResultPanel title="候選藥物" rows={recommendation.ranked_therapies} primary="name" secondary="matched_genes" />
            <ResultPanel title="相關臨床試驗" rows={recommendation.matching_trials} primary="brief_title" secondary="nct_id" />
            <ResultPanel title="支持證據" rows={recommendation.supporting_evidence} primary="title" secondary="source_name" />
            <ResultPanel title="科學中藥研究" rows={recommendation.herb_research} primary="chinese_name" secondary="matched_genes" />
            <ResultPanel title="交互作用" rows={recommendation.interaction_warnings} primary="interaction_type" secondary="severity" />
            <ResultPanel title="相似病例" rows={similar} primary="similar_case_id" secondary="score" />
          </div>
        </section>
      )}

      {loading && <div className="mt-5 rounded border bg-white p-4 text-gray-500">處理中…</div>}
    </main>
  )
}

function Metric({ label, value }: { label: string; value?: number }) {
  return <div className="rounded-lg border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value ?? 0}</div></div>
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3">{children}</div></section>
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs text-indigo-700">{children}</span>
}

function Empty() { return <div className="py-6 text-sm text-gray-500">尚無資料。</div> }

function ResultPanel({ title, rows, primary, secondary }: { title: string; rows: Array<Record<string, any>>; primary: string; secondary: string }) {
  return (
    <Panel title={`${title} (${rows.length})`}>
      {rows.map((row, index) => (
        <article key={`${title}-${index}`} className="border-b py-3 last:border-0">
          <div className="font-semibold">{String(row[primary] ?? '—')}</div>
          <div className="mt-1 text-xs text-gray-500">{Array.isArray(row[secondary]) ? row[secondary].join(', ') : String(row[secondary] ?? '—')}</div>
        </article>
      ))}
      {rows.length === 0 && <Empty />}
    </Panel>
  )
}
