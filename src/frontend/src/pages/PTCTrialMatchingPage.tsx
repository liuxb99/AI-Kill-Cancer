import { useEffect, useMemo, useState } from 'react'

import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'
import { getPTCTrialMatches, type TrialMatchingResponse } from '../api/ptcTrialMatching'

export default function PTCTrialMatchingPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [activeOnly, setActiveOnly] = useState(true)
  const [data, setData] = useState<TrialMatchingResponse | null>(null)
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

  const selectedCase = useMemo(() => cases.find((item) => item.case_id === caseId) || null, [cases, caseId])
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  async function runMatching() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getPTCTrialMatches(caseId, gene || undefined, activeOnly))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法比对临床试验')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-emerald-600">PTC Explainable Trial Navigator</p>
        <h1 className="text-3xl font-bold">病例与临床试验资格差距比对</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          依公开研究病例的基因、变异、Stage、年龄区间、性别与已同步试验条件逐项比对。未知资料不会算作符合，结果也不等同真实入组资格。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="grid gap-4 rounded-xl border bg-white p-5 shadow-sm md:grid-cols-4">
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
        <label className="flex items-end gap-2 pb-2 text-sm font-medium">
          <input type="checkbox" checked={activeOnly} onChange={(event) => setActiveOnly(event.target.checked)} />
          仅显示活动中试验
        </label>
        <div className="flex items-end">
          <button className="w-full rounded bg-emerald-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void runMatching()}>
            {loading ? '比对中…' : '开始试验比对'}
          </button>
        </div>
      </section>

      {data && (
        <div className="mt-6 space-y-5">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="试验总数" value={data.summary.total} />
            <Metric label="可能匹配" value={data.summary.potential_match} />
            <Metric label="资料不足" value={data.summary.insufficient_data} />
            <Metric label="明确不符" value={data.summary.unlikely_match} />
          </section>

          <section className="space-y-4">
            {data.matches.map((item) => (
              <article key={item.nct_id} className="overflow-hidden rounded-xl border bg-white shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4 border-b bg-slate-50 p-5">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-emerald-600">{item.nct_id} · {item.status || 'status unknown'}</div>
                    <h2 className="mt-1 text-xl font-bold">{item.title}</h2>
                    <p className="mt-1 text-sm text-gray-500">{item.phases.join(', ') || 'Phase 未提供'} · {item.target_genes.join(', ') || '无结构化目标基因'}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-emerald-700">{item.score.toFixed(1)}</div>
                    <div className="text-xs uppercase text-gray-500">{classificationLabel(item.classification)}</div>
                  </div>
                </div>

                <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">
                  {item.criteria.map((criterion) => (
                    <div key={criterion.name} className={`rounded border p-3 ${criterionClass(criterion.status)}`}>
                      <div className="flex justify-between gap-3"><strong>{criterion.name}</strong><span>{criterion.awarded}/{criterion.weight}</span></div>
                      <div className="mt-1 text-sm">{criterion.detail}</div>
                    </div>
                  ))}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t p-5 text-sm">
                  <div className="space-y-1">
                    <div><strong>阻塞条件：</strong>{item.blocking_mismatches.join(', ') || '无明确阻塞'}</div>
                    <div><strong>缺少／未解析：</strong>{item.missing_or_unparsed.join(', ') || '无'}</div>
                  </div>
                  {item.source_url && <a className="rounded border border-emerald-300 px-3 py-2 font-semibold text-emerald-700" href={item.source_url} target="_blank" rel="noreferrer">打开 ClinicalTrials.gov</a>}
                </div>
              </article>
            ))}
            {data.matches.length === 0 && <div className="rounded-xl border border-dashed bg-white p-12 text-center text-gray-500">没有符合当前筛选条件的已同步试验。</div>}
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

function criterionClass(status: 'match' | 'mismatch' | 'unknown'): string {
  if (status === 'match') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (status === 'mismatch') return 'border-red-200 bg-red-50 text-red-900'
  return 'border-amber-200 bg-amber-50 text-amber-900'
}

function classificationLabel(value: TrialMatchingResponse['matches'][number]['classification']): string {
  if (value === 'potential_match') return 'potential match'
  if (value === 'unlikely_match') return 'unlikely match'
  return 'insufficient data'
}
