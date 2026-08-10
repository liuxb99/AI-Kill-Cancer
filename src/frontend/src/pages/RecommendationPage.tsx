import { Fragment, useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiRequest } from '../api/client'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'
import DualModeSelector from '../components/DualModeSelector'

interface Explanation { category: string; detail: string; source: string; score_impact: number }
interface DrugItem { drug_name: string; rank: number; overall_score: number; evidence_score: number; sensitivity_score: number; resistance_score: number; explanations: Explanation[] }
interface RecommendationResult { recommendation_id: string; patient_id: string; recommendations: DrugItem[]; trace_id: string; engine_version: string; created_at: string }
type DemoCase = { case_key: string; variant: { gene?: string; hgvs_p?: string; variant_type?: string }; drug?: { name?: string }; evidence?: { level?: string; synthetic?: boolean } }

export async function fetchRecommendation(patientId: string, variants: string[], topN: number): Promise<RecommendationResult> { return apiRequest<RecommendationResult>('/recommendation', { method: 'POST', body: JSON.stringify({ patient_id: patientId, variants, top_n: topN }) }) }
function scoreClass(value: number): string { if (value >= 0.7) return 'text-green-600'; if (value >= 0.4) return 'text-amber-600'; return 'text-red-600' }
function caseLabel(item: PTCLatestCase): string { const genes = Array.from(new Set(item.variants.map((variant) => variant.gene))).slice(0, 3).join(', '); return `${item.case_id} · ${item.pathologic_stage || 'Stage —'} · ${genes || 'No variants'}` }

export default function RecommendationPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const demoCaseKey = searchParams.get('demo_case')
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [patientId, setPatientId] = useState('')
  const [advancedPatientId, setAdvancedPatientId] = useState('')
  const [variantsText, setVariantsText] = useState('')
  const [topN, setTopN] = useState(5)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecommendationResult | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [demoContext, setDemoContext] = useState<DemoCase | null>(null)

  useEffect(() => {
    if (demoCaseKey) {
      fetch('/api/v1/demo/cases').then((response) => response.ok ? response.json() : Promise.reject(new Error('demo API failed'))).then((data) => {
        const selected = (Array.isArray(data.items) ? data.items : []).find((item: DemoCase) => item.case_key === demoCaseKey)
        if (!selected) throw new Error(`找不到 Demo Case：${demoCaseKey}`)
        setDemoContext(selected); setPatientId(selected.case_key); setVariantsText(`${selected.variant.gene || ''} ${selected.variant.hgvs_p || selected.variant.variant_type || ''}`.trim()); setError(null)
      }).catch((reason) => setError(reason instanceof Error ? reason.message : '無法載入 Demo Case')).finally(() => setLoading(false))
      return
    }
    void getLatestPTCCases(100).then((response) => { setCases(response.cases); const first = response.cases[0]; if (first) selectCase(first.case_id, response.cases) }).catch((reason) => setError(reason instanceof Error ? reason.message : '無法載入病例')).finally(() => setLoading(false))
  }, [demoCaseKey])

  const variants = useMemo(() => variantsText.split('\n').map((item) => item.trim()).filter(Boolean), [variantsText])
  function selectCase(caseId: string, source = cases) { const selected = source.find((item) => item.case_id === caseId); if (!selected) return; setDemoContext(null); setPatientId(selected.case_id); setVariantsText(selected.variants.map((variant) => `${variant.gene} ${variant.protein_change || variant.classification || variant.variant_id || ''}`.trim()).join('\n')); setResult(null); setError(null) }
  function useAdvancedInput() { const normalized = advancedPatientId.trim(); if (!normalized) return; setDemoContext(null); setPatientId(normalized); setVariantsText(''); setResult(null); setError(null) }
  async function generate() { if (!patientId.trim()) { setError('請選擇病例或輸入 Patient ID'); return } if (variants.length === 0) { setError('請至少提供一個 Variant'); return } setLoading(true); setError(null); setResult(null); try { setResult(await fetchRecommendation(patientId.trim(), variants, topN)) } catch (reason) { setError(reason instanceof Error ? reason.message : '推薦請求失敗') } finally { setLoading(false) } }
  function toggleDrug(name: string) { setExpanded((current) => { const next = new Set(current); next.has(name) ? next.delete(name) : next.add(name); return next }) }

  const recentContent = <div className="p-4">{loading && cases.length === 0 ? <p className="text-sm text-slate-500">載入病例中…</p> : cases.length === 0 ? <p className="text-sm text-slate-500">目前沒有可選擇的病例。</p> : <label className="block text-sm font-medium text-slate-700">最近 100 個 PTC 病例<select aria-label="最近 100 個 PTC 病例" value={cases.some((item) => item.case_id === patientId) ? patientId : ''} onChange={(event) => selectCase(event.target.value)} className="mt-2 w-full rounded-lg border px-3 py-2">{cases.map((item) => <option key={item.case_id} value={item.case_id}>{caseLabel(item)}</option>)}</select></label>}</div>

  return <main className="mx-auto max-w-6xl px-4 py-8">
    <header className="mb-6 flex items-center gap-4"><button onClick={() => navigate('/')} className="text-xl text-gray-400 hover:text-primary-600">←</button><div><p className="text-sm font-semibold text-primary-600">Explainable Drug Ranking</p><h1 className="text-3xl font-bold">藥物推薦</h1><p className="mt-1 text-gray-600">一般模式選最近 100 個 PTC 病例；首頁 Demo deep link 會自動帶入同一 synthetic case 與 variant。</p></div></header>
    {demoContext && <section className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-amber-700">Synthetic Demo Context</p><p className="font-semibold">{demoContext.case_key} · {demoContext.variant.gene} {demoContext.variant.hgvs_p}</p><p className="text-xs text-amber-700">展示藥物：{demoContext.drug?.name || '—'} · Evidence {demoContext.evidence?.level || '—'}。此資料僅用於軟體流程展示。</p></div><button onClick={() => navigate('/')} className="rounded border border-amber-300 px-3 py-2 text-sm">切換 Demo Case</button></div></section>}
    {!demoContext && <DualModeSelector title="選擇推薦病例" description="最近病例與自訂 Patient ID 共用同一個推薦結果區。" recentContent={recentContent} advancedLabel="自訂 Patient ID" advancedPlaceholder="輸入 Patient ID 後自行填寫 Variants" advancedValue={advancedPatientId} onAdvancedValueChange={setAdvancedPatientId} onAdvancedSubmit={useAdvancedInput} advancedDisabled={!advancedPatientId.trim()} advancedLoading={loading} advancedHelp={error || '精準查詢會切換至手動 Variant 輸入模式。'} />}
    <section className="mt-5 rounded-xl border bg-white p-5 shadow-sm"><div className="grid gap-4 md:grid-cols-[1fr_160px]"><label className="text-sm font-medium">Variants（每行一個）<textarea aria-label="Variants" rows={6} value={variantsText} onChange={(event) => setVariantsText(event.target.value)} placeholder="BRAF V600E\nRET fusion" className="mt-1 w-full rounded border px-3 py-2 font-mono text-sm" /></label><label className="text-sm font-medium">Top N<select value={topN} onChange={(event) => setTopN(Number(event.target.value))} className="mt-1 w-full rounded border px-3 py-2">{Array.from({ length: 10 }, (_, index) => index + 1).map((number) => <option key={number} value={number}>{number}</option>)}</select></label></div><div className="mt-4 flex items-center justify-between gap-3"><div className="text-sm text-gray-500">目前 Patient ID：<strong>{patientId || '尚未選擇'}</strong> · {variants.length} variants</div><button onClick={() => void generate()} disabled={loading || !patientId || variants.length === 0} className="rounded bg-primary-600 px-5 py-2.5 font-semibold text-white disabled:opacity-40">{loading ? '生成中…' : '產生推薦'}</button></div>{error && <p className="mt-3 text-sm text-red-600">{error}</p>}</section>
    {result && <section className="mt-6 overflow-hidden rounded-xl border bg-white shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4"><div><h2 className="font-bold">推薦結果 · {result.patient_id}</h2><p className="text-xs text-gray-500">{result.engine_version} · {result.trace_id}</p></div><button onClick={() => navigate(`/clinical-decision/${result.recommendation_id}`)} className="rounded border px-3 py-2 text-sm text-primary-700">查看臨床決策 →</button></div><div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs uppercase text-gray-500"><tr><th className="px-4 py-3">Rank</th><th className="px-4 py-3">Drug</th><th className="px-4 py-3">Overall</th><th className="px-4 py-3">Evidence</th><th className="px-4 py-3">Sensitivity</th><th className="px-4 py-3">Resistance</th></tr></thead><tbody className="divide-y">{result.recommendations.map((drug) => <Fragment key={drug.drug_name}><tr className="cursor-pointer hover:bg-gray-50" onClick={() => toggleDrug(drug.drug_name)}><td className="px-4 py-3">{drug.rank}</td><td className="px-4 py-3 font-semibold">{drug.drug_name}</td><td className={`px-4 py-3 ${scoreClass(drug.overall_score)}`}>{drug.overall_score.toFixed(3)}</td><td className="px-4 py-3">{drug.evidence_score.toFixed(3)}</td><td className="px-4 py-3">{drug.sensitivity_score.toFixed(3)}</td><td className="px-4 py-3">{drug.resistance_score.toFixed(3)}</td></tr>{expanded.has(drug.drug_name) && <tr><td colSpan={6} className="bg-gray-50 px-6 py-4"><div className="space-y-2">{drug.explanations.map((item, index) => <article key={index} className="rounded border bg-white p-3"><div className="flex justify-between gap-3"><strong>{item.category}</strong><span className={item.score_impact >= 0 ? 'text-green-600' : 'text-red-600'}>{item.score_impact >= 0 ? '+' : ''}{item.score_impact}</span></div><p className="mt-1 text-gray-700">{item.detail}</p><p className="mt-1 text-xs text-gray-400">來源：{item.source}</p></article>)}</div></td></tr>}</Fragment>)}</tbody></table></div></section>}
  </main>
}
