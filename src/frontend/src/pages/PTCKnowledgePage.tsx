import { useEffect, useState, type ReactNode } from 'react'

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

export default function PTCKnowledgePage() {
  const [therapies, setTherapies] = useState<PTCTherapy[]>([])
  const [trials, setTrials] = useState<PTCTrial[]>([])
  const [evidence, setEvidence] = useState<PTCEvidence[]>([])
  const [gene, setGene] = useState('BRAF')
  const [drugNames, setDrugNames] = useState('selpercatinib, larotrectinib, dabrafenib')
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadAll() {
    setLoading(true)
    setError(null)
    try {
      const [therapyRows, trialRows, evidenceRows] = await Promise.all([
        listPTCTherapies(),
        listPTCTrials(),
        listPTCEvidence(),
      ])
      setTherapies(therapyRows)
      setTrials(trialRows)
      setEvidence(evidenceRows)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 知識資料')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAll()
  }, [])

  async function filterGene() {
    setLoading(true)
    setError(null)
    try {
      const result = await getPTCGeneKnowledge(gene.trim().toUpperCase())
      setTherapies(result.therapies)
      setTrials(result.trials)
      setEvidence(result.evidence)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法查詢基因知識')
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
      const names = drugNames.split(',').map((item) => item.trim()).filter(Boolean)
      const result = await syncPTCOpenFDA(names)
      setMessage(`openFDA 標籤同步完成：${result.records} 筆`)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'openFDA 同步失敗')
    }
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">PTC Precision Oncology</p>
        <h1 className="text-3xl font-bold">藥物、證據與臨床試驗</h1>
        <p className="mt-2 text-gray-600">從公開來源同步可追溯資料；內容供研究與決策支援，不直接構成醫療建議。</p>
      </section>

      <section className="mb-6 grid gap-4 rounded-lg border bg-white p-5 shadow-sm lg:grid-cols-2">
        <div>
          <h2 className="font-semibold">ClinicalTrials.gov</h2>
          <p className="mt-1 text-sm text-gray-500">同步 Papillary Thyroid Carcinoma 相關研究。</p>
          <button className="mt-3 rounded bg-primary-600 px-4 py-2 text-white" onClick={() => void syncTrials()}>同步臨床試驗</button>
        </div>
        <div>
          <h2 className="font-semibold">openFDA 藥物標籤</h2>
          <input className="mt-2 w-full rounded border px-3 py-2 text-sm" value={drugNames} onChange={(event) => setDrugNames(event.target.value)} aria-label="藥物名稱" />
          <button className="mt-3 rounded bg-primary-600 px-4 py-2 text-white" onClick={() => void syncLabels()}>同步藥物標籤</button>
        </div>
      </section>

      <section className="mb-6 flex flex-wrap gap-3">
        <input className="w-56 rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value.toUpperCase())} aria-label="基因" />
        <button className="rounded border px-4 py-2" onClick={() => void filterGene()}>查詢基因鏈</button>
        <button className="rounded border px-4 py-2" onClick={() => void loadAll()}>顯示全部</button>
      </section>

      {message && <div className="mb-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">{message}</div>}
      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {loading && <div className="mb-4 rounded border bg-white p-5 text-gray-500">載入中…</div>}

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel title={`Therapies (${therapies.length})`}>
          {therapies.map((item) => <article key={item.therapy_key} className="border-b py-3 last:border-0"><div className="font-semibold">{item.name}</div><div className="text-xs text-gray-500">{item.generic_name || '—'} · {item.source_name}</div>{item.mechanism && <p className="mt-2 text-sm text-gray-700">{item.mechanism}</p>}{item.indications.slice(0, 2).map((text, index) => <p key={index} className="mt-1 text-xs text-gray-500">{text}</p>)}</article>)}
          {therapies.length === 0 && <Empty />}
        </Panel>
        <Panel title={`Evidence (${evidence.length})`}>
          {evidence.map((item) => <article key={item.evidence_key} className="border-b py-3 last:border-0"><div className="font-semibold">{item.title || item.source_name}</div><div className="text-xs text-gray-500">{item.source_name} · {item.evidence_level || '未分級'}</div>{item.summary && <p className="mt-2 text-sm text-gray-700">{item.summary}</p>}</article>)}
          {evidence.length === 0 && <Empty />}
        </Panel>
        <Panel title={`Clinical Trials (${trials.length})`}>
          {trials.map((item) => <article key={item.nct_id} className="border-b py-3 last:border-0"><div className="font-semibold">{item.brief_title}</div><div className="text-xs text-gray-500">{item.nct_id} · {item.overall_status || 'Status unknown'}</div><div className="mt-2 flex flex-wrap gap-1">{item.interventions.slice(0, 4).map((intervention, index) => <span key={`${item.nct_id}-${index}`} className="rounded bg-indigo-50 px-2 py-1 text-xs text-indigo-700">{intervention.name || intervention.type || 'Intervention'}</span>)}</div></article>)}
          {trials.length === 0 && <Empty />}
        </Panel>
      </div>
    </main>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3">{children}</div></section>
}

function Empty() {
  return <div className="py-6 text-sm text-gray-500">尚無資料，請先執行同步。</div>
}
