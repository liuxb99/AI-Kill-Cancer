import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getPTCSimilarCases, type PTCCohortResponse } from '../api/ptcCohort'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCCohortPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(20)
  const [minScore, setMinScore] = useState(0)
  const [data, setData] = useState<PTCCohortResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getLatestPTCCases(100)
      .then((result) => {
        setCases(result.cases)
        if (result.cases[0]) setCaseId(result.cases[0].case_id)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '无法载入病例'))
  }, [])

  const filtered = useMemo(() => {
    const text = query.trim().toUpperCase()
    if (!text) return cases
    return cases.filter((item) =>
      item.case_id.toUpperCase().includes(text)
      || (item.pathologic_stage || '').toUpperCase().includes(text)
      || item.variants.some((variant) => variant.gene.toUpperCase().includes(text)),
    )
  }, [cases, query])

  async function compare() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getPTCSimilarCases(caseId, limit, minScore))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法比较病例')
    } finally {
      setLoading(false)
    }
  }

  function openCase(targetCaseId: string, target: '3d' | 'assistant' | 'report') {
    const path = target === '3d' ? '/ptc-3d' : target === 'assistant' ? '/ptc-assistant' : '/ptc-reports'
    navigate(`${path}?case=${encodeURIComponent(targetCaseId)}`)
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-teal-600">PTC Explainable Cohort Explorer</p>
        <h1 className="text-3xl font-bold">PTC 相似病例与 Outcome 队列比较</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          使用可解释规则比较去识别化公开研究病例。评分来自共同基因、蛋白变异、Stage、TNM、年龄与性别，不是预测模型。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="grid gap-4 rounded-xl border bg-white p-5 shadow-sm md:grid-cols-2 xl:grid-cols-5">
        <label className="text-sm font-medium xl:col-span-2">病例搜索
          <input aria-label="搜索队列病例" className="mt-1 w-full rounded border px-3 py-2" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="病例号、Stage、BRAF、RET…" />
        </label>
        <label className="text-sm font-medium">锚点病例
          <select className="mt-1 w-full rounded border px-3 py-2" value={caseId} onChange={(event) => { setCaseId(event.target.value); setData(null) }}>
            {filtered.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id} · {item.pathologic_stage || 'Stage —'}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">返回数量
          <input className="mt-1 w-full rounded border px-3 py-2" type="number" min={1} max={100} value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
        </label>
        <label className="text-sm font-medium">最低分数
          <input className="mt-1 w-full rounded border px-3 py-2" type="number" min={0} max={100} value={minScore} onChange={(event) => setMinScore(Number(event.target.value))} />
        </label>
        <div className="md:col-span-2 xl:col-span-5">
          <button className="rounded bg-teal-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void compare()}>{loading ? '比较中…' : '寻找相似病例'}</button>
        </div>
      </section>

      {data && (
        <div className="mt-6 space-y-5">
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric label="相似队列" value={String(data.cohort.size)} />
            <Metric label="平均追踪天数" value={data.cohort.mean_follow_up_days?.toFixed(0) || '—'} />
            <Metric label="锚点基因" value={data.anchor.genes.join(', ') || '—'} />
            <Metric label="锚点 Stage" value={data.anchor.pathologic_stage || '—'} />
          </section>

          <section className="grid gap-5 xl:grid-cols-3">
            <Distribution title="Stage 分布" values={data.cohort.stage_distribution} />
            <Distribution title="Vital status 分布" values={data.cohort.vital_status_distribution} />
            <section className="rounded-xl border bg-white p-5 shadow-sm"><h2 className="font-bold">队列常见基因</h2><div className="mt-3 space-y-2">{data.cohort.top_genes.map((item) => <div key={item.gene} className="flex justify-between rounded bg-slate-50 px-3 py-2 text-sm"><strong>{item.gene}</strong><span>{item.cases} cases</span></div>)}</div></section>
          </section>

          <section className="rounded-xl border bg-white shadow-sm">
            <div className="border-b px-5 py-4"><h2 className="text-xl font-bold">相似病例排名</h2><p className="text-sm text-gray-500">每笔结果均列出评分组成，方便核对为何被判为相似。</p></div>
            <div className="divide-y">
              {data.matches.map((item, index) => (
                <article key={item.case_id} className="p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><div className="text-xs text-gray-400">#{index + 1}</div><h3 className="text-lg font-bold">{item.case_id}</h3><p className="text-sm text-gray-500">{item.case_facts.pathologic_stage || 'Stage —'} · {item.case_facts.vital_status || 'Outcome —'}</p></div>
                    <div className="rounded-full bg-teal-100 px-4 py-2 text-lg font-bold text-teal-800">{item.score.toFixed(1)}</div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">{Object.entries(item.components).map(([name, value]) => <span key={name} className="rounded bg-slate-100 px-2 py-1">{name}: {value.toFixed(1)}</span>)}</div>
                  <p className="mt-3 text-sm"><strong>共同基因：</strong>{item.shared_genes.join(', ') || '无'}</p>
                  <p className="mt-1 text-sm"><strong>共同蛋白变异：</strong>{item.shared_protein_variants.join(', ') || '无'}</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openCase(item.case_id, '3d')}>打开 3D</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openCase(item.case_id, 'assistant')}>研究助手</button>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => openCase(item.case_id, 'report')}>研究报告</button>
                  </div>
                </article>
              ))}
              {data.matches.length === 0 && <div className="p-10 text-center text-gray-500">没有达到最低分数的病例。</div>}
            </div>
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{data.disclaimer}</section>
        </div>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-xl font-bold">{value}</div></div>
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  return <section className="rounded-xl border bg-white p-5 shadow-sm"><h2 className="font-bold">{title}</h2><div className="mt-3 space-y-2">{Object.entries(values).map(([name, count]) => <div key={name} className="flex justify-between rounded bg-slate-50 px-3 py-2 text-sm"><span>{name}</span><strong>{count}</strong></div>)}</div></section>
}
