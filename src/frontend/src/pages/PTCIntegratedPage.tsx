import { useEffect, useState, type ReactNode } from 'react'

import DualModeSelector from '../components/DualModeSelector'
import DemoContextBanner, { useDemoContext } from '../components/DemoContextBanner'
import { getPTCCase } from '../api/ptcResearch'
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
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCIntegratedPage() {
  const { synthetic, context: demoContext, loading: demoLoading, error: demoError } = useDemoContext()
  const [dashboard, setDashboard] = useState<PTCDashboard | null>(null)
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [selectedCase, setSelectedCase] = useState('')
  const [exactCaseId, setExactCaseId] = useState('')
  const [advancedCase, setAdvancedCase] = useState<PTCLatestCase | null>(null)
  const [herbs, setHerbs] = useState<PTCHerb[]>([])
  const [interactions, setInteractions] = useState<PTCInteraction[]>([])
  const [recommendation, setRecommendation] = useState<PTCIntegratedRecommendation | null>(null)
  const [similar, setSimilar] = useState<Array<Record<string, any>>>([])
  const [loading, setLoading] = useState(!synthetic)
  const [advancedLoading, setAdvancedLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    if (synthetic) return
    setLoading(true)
    setError(null)
    try {
      const [summary, caseRows, herbRows, interactionRows] = await Promise.all([
        getPTCIntegratedDashboard(),
        getLatestPTCCases(100),
        listPTCHerbs(),
        listPTCInteractions(),
      ])
      setDashboard(summary)
      setCases(caseRows.cases)
      setSelectedCase((current) => current || caseRows.cases[0]?.case_id || '')
      setHerbs(herbRows.slice(0, 100))
      setInteractions(interactionRows.slice(0, 100))
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 整合工作台')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!synthetic) void load()
  }, [synthetic])

  async function bootstrap() {
    if (synthetic) return
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

  async function queryExactCase() {
    const normalized = exactCaseId.trim()
    if (!normalized || synthetic) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const record = await getPTCCase(normalized)
      const converted = record as PTCLatestCase
      setAdvancedCase(converted)
      setSelectedCase(converted.case_id)
      setRecommendation(null)
      setSimilar([])
    } catch (err) {
      setError(err instanceof Error ? err.message : '資料庫找不到指定病例')
    } finally {
      setAdvancedLoading(false)
    }
  }

  async function analyse() {
    if (!selectedCase || synthetic) return
    setLoading(true)
    setError(null)
    try {
      const [rec, similarRows] = await Promise.all([
        generatePTCIntegratedRecommendation(selectedCase),
        calculatePTCSimilarity(selectedCase),
      ])
      setRecommendation(rec)
      setSimilar(similarRows.slice(0, 100))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PTC 研究分析失敗')
    } finally {
      setLoading(false)
    }
  }

  if (synthetic) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8">
        <section className="mb-6">
          <p className="text-sm font-semibold text-primary-600">PTC Research Workbench</p>
          <h1 className="text-3xl font-bold">甲狀腺乳突癌整合研究工作台</h1>
          <p className="mt-2 text-gray-600">Synthetic showcase 只投影 bundled demo case，不執行資料同步、正式病例查詢或研究分析寫入。</p>
        </section>
        {demoError && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{demoError}</div>}
        {demoLoading ? <div className="rounded border bg-white p-8 text-center text-gray-500">載入 Demo Case…</div> : demoContext ? (
          <>
            <DemoContextBanner context={demoContext} label="PTC Integrated Synthetic Demo" />
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Metric label="Demo Case" textValue={demoContext.case_key} />
              <Metric label="Driver Gene" textValue={demoContext.variant.gene || '—'} />
              <Metric label="Evidence" textValue={demoContext.evidence.level || '—'} />
              <Metric label="Trial" textValue={demoContext.clinical_trial.id || '—'} />
            </section>
            <section className="mt-6 grid gap-6 xl:grid-cols-3">
              <Panel title="Case → Variant">
                <Info label="Cancer Type" value={demoContext.cancer_type} />
                <Info label="Stage" value={demoContext.stage} />
                <Info label="Gene" value={demoContext.variant.gene} />
                <Info label="Protein" value={demoContext.variant.hgvs_p} />
                <Info label="Driver" value={demoContext.variant.driver_status} />
              </Panel>
              <Panel title="Evidence → Drug">
                <Info label="Evidence Level" value={demoContext.evidence.level} />
                <Info label="Direction" value={demoContext.evidence.direction} />
                <Info label="Drug" value={demoContext.drug.name} />
                <Info label="Mechanism" value={demoContext.drug.mechanism} />
                <p className="mt-3 text-sm text-gray-600">{demoContext.evidence.summary || 'Synthetic evidence summary unavailable.'}</p>
              </Panel>
              <Panel title="Publication → Trial">
                <Info label="Publication" value={demoContext.publication.title} />
                <Info label="Journal" value={demoContext.publication.journal} />
                <Info label="Trial" value={demoContext.clinical_trial.id} />
                <Info label="Status" value={demoContext.clinical_trial.status} />
              </Panel>
            </section>
            <section className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50 p-5 text-sm text-indigo-900">
              <strong>Demo isolation:</strong> 本頁在 synthetic mode 不呼叫 dashboard、最近病例、整合推薦、相似病例、中藥 bootstrap 或 interaction API；這避免 Vercel ephemeral demo 被正式研究資料依賴拖垮。
            </section>
          </>
        ) : <div className="rounded border bg-white p-8 text-gray-500">找不到指定 Demo Case。</div>}
      </main>
    )
  }

  const recentContent = (
    <div className="p-4">
      <label className="text-sm font-medium">最近 100 個研究病例
        <select className="mt-1 w-full rounded border px-3 py-2" value={advancedCase ? '' : selectedCase} onChange={(event) => { setAdvancedCase(null); setSelectedCase(event.target.value); setRecommendation(null); setSimilar([]) }}>
          <option value="">尚無病例</option>
          {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'stage unknown'}</option>)}
        </select>
      </label>
    </div>
  )

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <section className="mb-6"><p className="text-sm font-semibold text-primary-600">PTC Research Workbench</p><h1 className="text-3xl font-bold">甲狀腺乳突癌整合研究工作台</h1><p className="mt-2 text-gray-600">一般模式從最近 100 個病例中選擇；進階模式可用完整 Case ID 查詢整個資料庫，再執行同一套整合分析。</p></section>
      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {message && <div className="mb-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-emerald-700">{message}</div>}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-7"><Metric label="病例" value={dashboard?.case_count} /><Metric label="變異" value={dashboard?.variant_count} /><Metric label="藥物" value={dashboard?.therapy_count} /><Metric label="證據" value={dashboard?.evidence_count} /><Metric label="試驗" value={dashboard?.trial_count} /><Metric label="中藥研究" value={dashboard?.herb_count} /><Metric label="交互作用" value={dashboard?.interaction_count} /></section>
      <div className="mt-6 grid gap-4 lg:grid-cols-[420px_1fr]">
        <DualModeSelector title="選擇整合分析病例" description="最近 100 筆與精準 Case ID 查詢共用同一套分析引擎。" recentContent={recentContent} advancedLabel="完整 Case ID" advancedPlaceholder="例如 TCGA-XX-YYYY" advancedValue={exactCaseId} onAdvancedValueChange={setExactCaseId} onAdvancedSubmit={queryExactCase} advancedLoading={advancedLoading} advancedHelp="進階查詢不受最近 100 筆限制；後端會驗證病例是否存在。" />
        <section className="rounded-xl border bg-white p-5 shadow-sm"><div className="text-xs text-gray-500">目前病例</div><div className="mt-1 text-xl font-bold">{selectedCase || '尚未選擇'}</div>{advancedCase && <div className="mt-1 text-xs font-semibold text-indigo-600">進階精準查詢結果</div>}<div className="mt-4 flex flex-wrap gap-3"><button className="rounded bg-primary-600 px-4 py-2 text-white disabled:opacity-50" disabled={!selectedCase || loading} onClick={() => void analyse()}>展示整合研究分析</button><button className="rounded border px-4 py-2" onClick={() => void bootstrap()}>建立固定科學中藥研究種子</button></div></section>
      </div>
      <section className="mt-6 grid gap-6 xl:grid-cols-3"><Panel title="高頻基因"><div className="space-y-2">{dashboard?.top_genes.slice(0, 100).map((item) => <div key={item.gene} className="flex justify-between rounded border px-3 py-2 text-sm"><span className="font-semibold">{item.gene}</span><span>{item.case_count} cases</span></div>)}</div></Panel><Panel title={`科學中藥研究 (${herbs.length})`}>{herbs.map((item) => <article key={item.herb_key} className="border-b py-3 last:border-0"><div className="font-semibold">{item.chinese_name} <span className="text-xs font-normal text-gray-500">{item.latin_name}</span></div><div className="mt-1 flex flex-wrap gap-1">{item.investigated_genes.map((itemGene) => <Tag key={itemGene}>{itemGene}</Tag>)}</div><p className="mt-2 text-xs text-amber-700">{item.evidence_level} · 不代表已證實治療效果</p></article>)}{herbs.length === 0 && <Empty />}</Panel><Panel title={`交互作用警告 (${interactions.length})`}>{interactions.map((item, index) => <article key={`${item.herb_key}-${item.therapy_key}-${index}`} className="border-b py-3 last:border-0"><div className="font-semibold">{item.herb_key}</div><div className="text-sm">↔ {item.therapy_key}</div><div className="mt-1 text-xs text-red-700">{item.severity} · {item.interaction_type}</div></article>)}{interactions.length === 0 && <Empty />}</Panel></section>
      {recommendation && <section className="mt-6 space-y-6"><div className="rounded-lg border bg-white p-5 shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-bold">研究分析：{recommendation.case_id}</h2><p className="text-sm text-gray-500">{recommendation.engine_version}</p></div><div className="rounded bg-indigo-50 px-3 py-2 text-indigo-700">Confidence {Math.round(recommendation.confidence * 100)}%</div></div><div className="mt-3 flex flex-wrap gap-2">{recommendation.genes.map((itemGene) => <Tag key={itemGene}>{itemGene}</Tag>)}</div><p className="mt-4 text-sm text-gray-700">{recommendation.explanation}</p></div><div className="grid gap-6 xl:grid-cols-3"><ResultPanel title="候選藥物" rows={recommendation.ranked_therapies.slice(0, 100)} primary="name" secondary="matched_genes" /><ResultPanel title="相關臨床試驗" rows={recommendation.matching_trials.slice(0, 100)} primary="brief_title" secondary="nct_id" /><ResultPanel title="支持證據" rows={recommendation.supporting_evidence.slice(0, 100)} primary="title" secondary="source_name" /><ResultPanel title="科學中藥研究" rows={recommendation.herb_research.slice(0, 100)} primary="chinese_name" secondary="matched_genes" /><ResultPanel title="交互作用" rows={recommendation.interaction_warnings.slice(0, 100)} primary="interaction_type" secondary="severity" /><ResultPanel title="相似病例" rows={similar} primary="similar_case_id" secondary="score" /></div></section>}
      {loading && <div className="mt-5 rounded border bg-white p-4 text-gray-500">處理中…</div>}
    </main>
  )
}

function Metric({ label, value, textValue }: { label: string; value?: number; textValue?: string }) { return <div className="rounded-lg border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{textValue ?? value ?? 0}</div></div> }
function Info({ label, value }: { label: string; value?: string | null }) { return <div className="border-b py-2 text-sm last:border-0"><div className="text-xs text-gray-500">{label}</div><div className="font-medium text-gray-900">{value || '—'}</div></div> }
function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3 max-h-[720px] overflow-y-auto">{children}</div></section> }
function Tag({ children }: { children: ReactNode }) { return <span className="rounded-full bg-indigo-50 px-2 py-1 text-xs text-indigo-700">{children}</span> }
function Empty() { return <div className="py-6 text-sm text-gray-500">資料庫目前沒有可展示資料。</div> }
function ResultPanel({ title, rows, primary, secondary }: { title: string; rows: Array<Record<string, any>>; primary: string; secondary: string }) { return <Panel title={`${title} (${rows.length})`}>{rows.map((row, index) => <article key={`${title}-${index}`} className="border-b py-3 last:border-0"><div className="font-semibold">{String(row[primary] ?? '—')}</div><div className="mt-1 text-xs text-gray-500">{Array.isArray(row[secondary]) ? row[secondary].join(', ') : String(row[secondary] ?? '—')}</div></article>)}{rows.length === 0 && <Empty />}</Panel> }
