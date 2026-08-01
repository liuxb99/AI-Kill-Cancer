import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getPTCEvidenceMatrix, type PTCEvidenceMatrixResponse } from '../api/ptcEvidenceMatrix'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCEvidenceMatrixPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
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
        setCaseId(initial?.case_id || '')
        setGene(params.get('gene')?.toUpperCase() || '')
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '无法载入病例'))
  }, [])

  const selectedCase = useMemo(
    () => cases.find((item) => item.case_id === caseId) || null,
    [cases, caseId],
  )
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  async function loadMatrix() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getPTCEvidenceMatrix(caseId, gene || undefined))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成证据矩阵')
    } finally {
      setLoading(false)
    }
  }

  function openTool(target: '3d' | 'literature' | 'report', rowGene: string) {
    const path = target === '3d' ? '/ptc-3d' : target === 'literature' ? '/ptc-3d' : '/ptc-reports'
    const view = target === 'literature' ? '&view=literature' : target === '3d' ? '&view=protein' : ''
    navigate(`${path}?case=${encodeURIComponent(caseId)}&gene=${encodeURIComponent(rowGene)}${view}`)
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-fuchsia-600">PTC Explainable Evidence Matrix</p>
        <h1 className="text-3xl font-bold">突变、药物、证据、试验与队列矩阵</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          将当前病例的每个基因／变异与已持久化药物、Evidence、临床试验、PMC 图表和同基因病例队列放在同一张可解释矩阵中。
          分数只表示资料完整度与关联程度，不代表治疗优先级或临床获益。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="grid gap-4 rounded-xl border bg-white p-5 shadow-sm md:grid-cols-3">
        <label className="text-sm font-medium">研究病例
          <select className="mt-1 w-full rounded border px-3 py-2" value={caseId} onChange={(event) => { setCaseId(event.target.value); setGene(''); setData(null) }}>
            {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">基因筛选
          <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value)}>
            <option value="">全部基因</option>
            {genes.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="flex items-end">
          <button className="w-full rounded bg-fuchsia-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void loadMatrix()}>
            {loading ? '生成中…' : '生成证据矩阵'}
          </button>
        </div>
      </section>

      {data && (
        <div className="mt-6 space-y-5">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <Metric label="基因" value={data.summary.genes} />
            <Metric label="药物" value={data.summary.therapies} />
            <Metric label="Evidence" value={data.summary.evidence} />
            <Metric label="Trials" value={data.summary.trials} />
            <Metric label="全文图表" value={data.summary.open_full_text_assets} />
            <Metric label="资料缺口" value={data.summary.unresolved_gaps} />
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
                  <div className="rounded-full bg-fuchsia-100 px-5 py-3 text-2xl font-bold text-fuchsia-800">{row.score.toFixed(1)}</div>
                </div>

                <div className="grid gap-5 p-5 xl:grid-cols-4">
                  <MatrixColumn title={`Therapies (${row.therapies.length})`} empty="没有已持久化药物">
                    {row.therapies.map((item) => <Card key={item.therapy_key} title={item.name} subtitle={item.approval_status || item.source || '—'} body={item.mechanism} />)}
                  </MatrixColumn>
                  <MatrixColumn title={`Evidence (${row.evidence.length})`} empty="没有 Evidence">
                    {row.evidence.map((item) => <Card key={item.evidence_key} title={item.title || item.evidence_key} subtitle={`${item.source || 'Unknown'} · ${item.level || 'ungraded'}`} body={`${item.figures} figures · ${item.tables} tables`} />)}
                  </MatrixColumn>
                  <MatrixColumn title={`Trials (${row.trials.length})`} empty="没有匹配试验">
                    {row.trials.map((item) => <Card key={item.nct_id} title={item.nct_id} subtitle={`${item.status || '—'}${item.active ? ' · active' : ''}`} body={item.title} />)}
                  </MatrixColumn>
                  <MatrixColumn title="Same-gene cohort" empty="没有同基因病例">
                    <Card title={`${row.cohort.same_gene_cases} cases`} subtitle="Vital status" body={formatDistribution(row.cohort.vital_status_distribution)} />
                    <Card title="Outcome" subtitle="Imported outcomes" body={formatDistribution(row.cohort.outcome_distribution)} />
                  </MatrixColumn>
                </div>

                <div className="grid gap-4 border-t p-5 lg:grid-cols-[1fr_auto]">
                  <div>
                    <h3 className="text-sm font-bold">评分组成</h3>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {Object.entries(row.score_components).map(([name, value]) => <span key={name} className="rounded bg-slate-100 px-2 py-1">{name}: {value.toFixed(1)}</span>)}
                    </div>
                    {row.gaps.length > 0 && <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><strong>资料缺口：</strong>{row.gaps.join('；')}</div>}
                  </div>
                  <div className="flex flex-wrap items-start gap-2">
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('3d', row.gene)}>蛋白 3D</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('literature', row.gene)}>论文图表</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openTool('report', row.gene)}>研究报告</button>
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

function MatrixColumn({ title, empty, children }: { title: string; empty: string; children: React.ReactNode }) {
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
