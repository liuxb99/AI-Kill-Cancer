import { useEffect, useMemo, useState, type ReactNode } from 'react'

import {
  getPTCGeneKnowledge,
  listPTCEvidence,
  listPTCTherapies,
  listPTCTrials,
  syncPTCClinicalTrials,
  syncPTCOpenFDA,
  type PTCEvidence,
  type PTCTherapy,
  type PTCTrial,
} from '../api/ptcResearch'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

const CURATED_OPENFDA_DRUGS = ['dabrafenib', 'selpercatinib', 'larotrectinib', 'entrectinib', 'trametinib']

export default function PTCKnowledgePage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [therapies, setTherapies] = useState<PTCTherapy[]>([])
  const [trials, setTrials] = useState<PTCTrial[]>([])
  const [evidence, setEvidence] = useState<PTCEvidence[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const selectedCase = useMemo(() => cases.find((item) => item.case_id === caseId) || null, [cases, caseId])
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  async function loadAll() {
    setLoading(true)
    setError(null)
    try {
      const [caseRows, therapyRows, trialRows, evidenceRows] = await Promise.all([
        getLatestPTCCases(100),
        listPTCTherapies(),
        listPTCTrials(),
        listPTCEvidence(),
      ])
      setCases(caseRows.cases)
      const initial = caseRows.cases[0]
      setCaseId((current) => current || initial?.case_id || '')
      setGene((current) => current || initial?.variants[0]?.gene?.toUpperCase() || '')
      setTherapies(therapyRows.slice(0, 100))
      setTrials(trialRows.slice(0, 100))
      setEvidence(evidenceRows.slice(0, 100))
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 知識資料')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [])

  useEffect(() => {
    if (genes.length && !genes.includes(gene)) setGene(genes[0])
    if (!genes.length) setGene('')
  }, [genes, gene])

  async function showSelectedGene(nextGene = gene) {
    if (!nextGene) return
    setLoading(true)
    setError(null)
    try {
      const result = await getPTCGeneKnowledge(nextGene)
      setTherapies(result.therapies.slice(0, 100))
      setTrials(result.trials.slice(0, 100))
      setEvidence(result.evidence.slice(0, 100))
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入所選基因知識')
    } finally {
      setLoading(false)
    }
  }

  async function syncTrials() {
    setMessage(null)
    setError(null)
    try {
      const result = await syncPTCClinicalTrials(100)
      setMessage(`ClinicalTrials.gov 同步完成：${result.records} 筆`)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : '臨床試驗同步失敗')
    }
  }

  async function syncLabels() {
    setMessage(null)
    setError(null)
    try {
      const result = await syncPTCOpenFDA(CURATED_OPENFDA_DRUGS)
      setMessage(`openFDA 固定研究藥物集合同步完成：${result.records} 筆`)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'openFDA 同步失敗')
    }
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">PTC Precision Oncology</p>
        <h1 className="text-3xl font-bold">藥物、證據與臨床試驗</h1>
        <p className="mt-2 text-gray-600">從資料庫最近 100 個公開病例中選擇病例與既有基因，再展示已同步的藥物、Evidence 與試驗資料。</p>
      </section>

      <section className="mb-6 grid gap-4 rounded-xl border bg-white p-5 shadow-sm lg:grid-cols-[1fr_1fr_auto]">
        <label className="text-sm font-medium">研究病例
          <select className="mt-1 w-full rounded border px-3 py-2" value={caseId} onChange={(event) => { setCaseId(event.target.value); setGene('') }}>
            {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">病例既有基因
          <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value)}>
            {genes.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button className="rounded bg-primary-600 px-4 py-2 text-white disabled:opacity-50" disabled={!gene || loading} onClick={() => void showSelectedGene()}>
            展示所選基因資料
          </button>
          <button className="rounded border px-4 py-2" onClick={() => void loadAll()}>展示全部前 100 筆</button>
        </div>
      </section>

      <section className="mb-6 grid gap-4 rounded-xl border bg-white p-5 shadow-sm lg:grid-cols-2">
        <div>
          <h2 className="font-semibold">ClinicalTrials.gov</h2>
          <p className="mt-1 text-sm text-gray-500">同步最多 100 筆 PTC 相關試驗。</p>
          <button className="mt-3 rounded border px-4 py-2" onClick={() => void syncTrials()}>同步試驗資料</button>
        </div>
        <div>
          <h2 className="font-semibold">openFDA 固定研究藥物集合</h2>
          <div className="mt-2 flex flex-wrap gap-2">{CURATED_OPENFDA_DRUGS.map((item) => <span key={item} className="rounded bg-slate-100 px-2 py-1 text-xs">{item}</span>)}</div>
          <button className="mt-3 rounded border px-4 py-2" onClick={() => void syncLabels()}>同步固定藥物集合</button>
        </div>
      </section>

      {message && <div className="mb-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">{message}</div>}
      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded border bg-white p-5 text-gray-500">載入中…</div>}

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title={`Therapies (${therapies.length})`}>
          {therapies.map((item) => <article key={item.therapy_key} className="border-b py-3 last:border-0"><div className="font-semibold">{item.name}</div><div className="text-xs text-gray-500">{item.generic_name || '—'} · {item.source_name}</div>{item.mechanism && <p className="mt-2 text-sm text-gray-700">{item.mechanism}</p>}</article>)}
          {therapies.length === 0 && <Empty />}
        </Panel>
        <Panel title={`Evidence (${evidence.length})`}>
          {evidence.map((item) => <article key={item.evidence_key} className="border-b py-3 last:border-0"><div className="font-semibold">{item.title || item.source_name}</div><div className="text-xs text-gray-500">{item.source_name} · {item.evidence_level || '未分級'}</div>{item.summary && <p className="mt-2 text-sm text-gray-700">{item.summary}</p>}</article>)}
          {evidence.length === 0 && <Empty />}
        </Panel>
        <Panel title={`Clinical Trials (${trials.length})`}>
          {trials.map((item) => <article key={item.nct_id} className="border-b py-3 last:border-0"><div className="font-semibold">{item.brief_title}</div><div className="text-xs text-gray-500">{item.nct_id} · {item.overall_status || 'Status unknown'}</div></article>)}
          {trials.length === 0 && <Empty />}
        </Panel>
      </div>
    </main>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3 max-h-[720px] overflow-y-auto">{children}</div></section>
}

function Empty() {
  return <div className="py-6 text-sm text-gray-500">資料庫目前沒有可展示資料。</div>
}
