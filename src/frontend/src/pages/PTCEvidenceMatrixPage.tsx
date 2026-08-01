import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { getPTCEvidenceMatrix, type PTCEvidenceMatrixResponse } from '../api/ptcEvidenceMatrix'
import { getPTCCase } from '../api/ptcResearch'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'
import DualModeSelector from '../components/DualModeSelector'

export default function PTCEvidenceMatrixPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [advancedCaseId, setAdvancedCaseId] = useState('')
  const [advancedLoading, setAdvancedLoading] = useState(false)
  const [data, setData] = useState<PTCEvidenceMatrixResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getLatestPTCCases(100)
      .then((result) => {
        setCases(result.cases)
        const params = new URLSearchParams(window.location.search)
        const requested = params.get('case')
        const initial = result.cases.find((item) => item.case_id === requested) || result.cases[0]
        setCaseId(initial?.case_id || requested || '')
        setAdvancedCaseId(requested || '')
        setGene(params.get('gene')?.toUpperCase() || '')
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '無法載入病例'))
  }, [])

  const selectedCase = useMemo(
    () => cases.find((item) => item.case_id === caseId) || null,
    [cases, caseId],
  )
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  async function exactCaseLookup() {
    const normalized = advancedCaseId.trim()
    if (!normalized) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const found = await getPTCCase(normalized)
      setCaseId(found.case_id)
      setGene('')
      setData(null)
      if (!cases.some((item) => item.case_id === found.case_id)) {
        setCases((current) => [{ ...found }, ...current].slice(0, 101) as PTCLatestCase[])
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '找不到指定病例')
    } finally {
      setAdvancedLoading(false)
    }
  }

  async function loadMatrix() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getPTCEvidenceMatrix(caseId, gene || undefined))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法生成證據矩陣')
    } finally {
      setLoading(false)
    }
  }

  function openTool(target: '3d' | 'literature' | 'report', rowGene: string) {
    const path = target === 'report' ? '/ptc-reports' : '/ptc-3d'
    const view = target === 'literature' ? '&view=literature' : target === '3d' ? '&view=protein' : ''
    navigate(`${path}?case=${encodeURIComponent(caseId)}&gene=${encodeURIComponent(rowGene)}${view}`)
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-fuchsia-600">PTC Explainable Evidence Matrix</p>
        <h1 className="text-3xl font-bold">突變、藥物、證據、試驗與隊列矩陣</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          將病例基因／變異與已持久化藥物、Evidence、臨床試驗、PMC 圖表和同基因病例隊列放在同一張矩陣中。
          分數只衡量資料鏈結與來源完整度；Outcome 僅於計分完成後描述，不代表療效、預後或治療優先級。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <DualModeSelector
        title="選擇研究病例"
        description="預設從資料庫最近 100 筆選擇；已知完整 Case ID 時，可查詢整個資料庫。"
        recentContent={(
          <div className="grid gap-4 p-5 md:grid-cols-3">
            <label className="text-sm font-medium">研究病例
              <select className="mt-1 w-full rounded border px-3 py-2" value={caseId} onChange={(event) => { setCaseId(event.target.value); setGene(''); setData(null) }}>
                {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'}</option>)}
              </select>
            </label>
            <label className="text-sm font-medium">基因篩選
              <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value)}>
                <option value="">全部基因</option>
                {genes.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <div className="flex items-end">
              <button className="w-full rounded bg-fuchsia-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void loadMatrix()}>
                {loading ? '生成中…' : '生成證據矩陣'}
              </button>
            </div>
          </div>
        )}
        advancedLabel="完整 Case ID"
        advancedPlaceholder="例如 TCGA-XX-XXXX"
        advancedValue={advancedCaseId}
        onAdvancedValueChange={setAdvancedCaseId}
        onAdvancedSubmit={exactCaseLookup}
        advancedLoading={advancedLoading}
        advancedHelp="精準查詢成功後，會使用同一套基因選擇與矩陣結果區。"
      />

      {data && (
        <div className="mt-6 space-y-5">
          <section className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
            <div className="font-bold">資料鏈結完整度計分</div>
            <div className="mt-1">版本：{data.methodology.scoring_version} · 最高 {data.methodology.maximum_score} 分 · Outcome-blind：{data.methodology.outcome_blind ? '是' : '否'}</div>
            <div className="mt-1 text-xs">排除欄位：{data.methodology.outcome_fields_excluded.join('、')}。同基因隊列僅於計分後描述。</div>
          </section>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <Metric label="基因" value={data.summary.genes} />
            <Metric label="藥物" value={data.summary.therapies} />
            <Metric label="Evidence" value={data.summary.evidence} />
            <Metric label="Trials" value={data.summary.trials} />
            <Metric label="全文圖表" value={data.summary.open_full_text_assets} />
            <Metric label="資料缺口" value={data.summary.unresolved_gaps} />
          </section>

          <section className="space-y-5">
            {data.rows.map((row) => (
              <article key={row.gene} className="overflow-hidden rounded-xl border bg-white shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4 border-b bg-slate-50 p-5">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-fuchsia-600">{row.pathway || 'Uncurated pathway'}</div>
                    <h2 className="text-2xl font-bold">{row.gene}</h2>
                    <p className="text-sm text-gray-500">{row.protein_domain || 'Protein domain unavailable'}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {row.variants.map((variant) => <span key={variant.variant_id} className="rounded bg-violet-100 px-2 py-1 text-xs text-violet-800">{variant.protein_change || variant.variant_id}</span>)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="rounded-full bg-fuchsia-100 px-5 py-3 text-2xl font-bold text-fuchsia-800">{row.score.toFixed(1)}</div>
                    <div className="mt-1 text-xs text-gray-500">資料鏈結完整度</div>
                  </div>
                </div>

                <div className="grid gap-5 p-5 xl:grid-cols-4">
                  <MatrixColumn title={`Therapies (${row.therapies.length})`} empty="沒有已持久化藥物">
                    {row.therapies.map((item) => <Card key={item.therapy_key} title={item.name} subtitle={item.approval_status || item.source || '—'} body={item.mechanism} />)}
                  </MatrixColumn>
                  <MatrixColumn title={`Evidence (${row.evidence.length})`} empty="沒有 Evidence">
                    {row.evidence.map((item) => <Card key={item.evidence_key} title={item.title || item.evidence_key} subtitle={`${item.source || 'Unknown'} · ${item.level || 'ungraded'}`} body={`${item.figures} figures · ${item.tables} tables`} />)}
                  </MatrixColumn>
                  <MatrixColumn title={`Trials (${row.trials.length})`} empty="沒有匹配試驗">
                    {row.trials.map((item) => <Card key={item.nct_id} title={item.nct_id} subtitle={`${item.status || '—'}${item.active ? ' · active' : ''}`} body={item.title} />)}
                  </MatrixColumn>
                  <MatrixColumn title="同基因隊列（計分後描述）" empty="沒有同基因病例">
                    <Card title={`${row.cohort.same_gene_cases} cases`} subtitle="Vital status，不參與分數" body={formatDistribution(row.cohort.vital_status_distribution)} />
                    <Card title="Outcome" subtitle="僅供配對後描述" body={formatDistribution(row.cohort.outcome_distribution)} />
                  </MatrixColumn>
                </div>

                <div className="grid gap-4 border-t p-5 lg:grid-cols-[1fr_auto]">
                  <div>
                    <h3 className="text-sm font-bold">完整度分數組成</h3>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {Object.entries(row.score_components).map(([name, value]) => <span key={name} className="rounded bg-slate-100 px-2 py-1">{name}: {value.toFixed(1)}</span>)}
                    </div>
                    {row.gaps.length > 0 && <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><strong>資料缺口：</strong>{row.gaps.join('；')}</div>}
                  </div>
                  <div className="flex flex-wrap items-start gap-2">
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('3d', row.gene)}>蛋白 3D</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('literature', row.gene)}>論文圖表</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('report', row.gene)}>研究報告</button>
                  </div>
                </div>
              </article>
            ))}
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{data.disclaimer}</section>
        </div>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div>
}

function MatrixColumn({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : []
  return <section><h3 className="font-bold">{title}</h3><div className="mt-2 space-y-2">{items.length ? items : <div className="rounded border border-dashed p-4 text-sm text-gray-400">{empty}</div>}</div></section>
}

function Card({ title, subtitle, body }: { title: string; subtitle?: string; body?: string }) {
  return <div className="rounded border p-3 text-sm"><strong>{title}</strong>{subtitle && <div className="text-xs text-gray-500">{subtitle}</div>}{body && <div className="mt-1 text-xs leading-5 text-gray-600">{body}</div>}</div>
}

function formatDistribution(values: Record<string, number>): string {
  const entries = Object.entries(values)
  return entries.length ? entries.map(([name, count]) => `${name}: ${count}`).join(' · ') : 'No imported data'
}
