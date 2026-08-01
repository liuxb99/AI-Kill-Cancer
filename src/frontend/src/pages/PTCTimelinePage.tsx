import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'
import { getPTCCaseTimeline, type PTCTimelineEvent, type PTCTimelineResponse } from '../api/ptcTimeline'

export default function PTCTimelinePage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [data, setData] = useState<PTCTimelineResponse | null>(null)
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
  const eventTypes = useMemo(
    () => Array.from(new Set((data?.events || []).map((item) => item.event_type))).sort(),
    [data],
  )
  const visibleEvents = useMemo(
    () => (data?.events || []).filter((item) => !typeFilter || item.event_type === typeFilter),
    [data, typeFilter],
  )

  async function loadTimeline() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getPTCCaseTimeline(caseId, gene || undefined))
      setTypeFilter('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成研究时间轴')
    } finally {
      setLoading(false)
    }
  }

  function executeAction(event: PTCTimelineEvent, actionType: string) {
    const selectedGene = event.gene || gene
    const suffix = `case=${encodeURIComponent(caseId)}${selectedGene ? `&gene=${encodeURIComponent(selectedGene)}` : ''}`
    if (actionType === 'open_3d') navigate(`/ptc-3d?${suffix}`)
    else if (actionType === 'open_protein') navigate(`/ptc-3d?${suffix}&view=protein`)
    else if (actionType === 'open_matrix') navigate(`/ptc-evidence-matrix?${suffix}`)
    else if (actionType === 'open_literature') navigate(`/ptc-3d?${suffix}&view=literature`)
    else if (actionType === 'open_trial' && event.source_url) window.open(event.source_url, '_blank', 'noopener,noreferrer')
  }

  return (
    <main className="mx-auto max-w-[1450px] px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-cyan-600">PTC Research Digital Thread</p>
        <h1 className="text-3xl font-bold">PTC 纵向研究时间轴</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          将病例入库、变异、Outcome、药物知识、Evidence、临床试验与同步批次按时间串成同一条可追溯链。
          每个时间点会明确标记是观察时间、抓取时间还是入库时间，避免误当成真实临床病程。
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
        <label className="text-sm font-medium">事件类型
          <select className="mt-1 w-full rounded border px-3 py-2" value={typeFilter} disabled={!data} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="">全部事件</option>
            {eventTypes.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="flex items-end">
          <button className="w-full rounded bg-cyan-600 px-5 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void loadTimeline()}>
            {loading ? '载入中…' : '生成 Digital Thread'}
          </button>
        </div>
      </section>

      {data && (
        <div className="mt-6 grid gap-5 xl:grid-cols-[280px_1fr]">
          <aside className="space-y-4">
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="font-bold">时间轴摘要</h2>
              <div className="mt-3 text-3xl font-bold text-cyan-700">{data.count}</div>
              <div className="text-sm text-gray-500">events</div>
              <div className="mt-4 space-y-2 text-sm">
                {Object.entries(data.summary.by_type).map(([name, count]) => <div key={name} className="flex justify-between rounded bg-slate-50 px-3 py-2"><span>{name}</span><strong>{count}</strong></div>)}
              </div>
            </section>
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="font-bold">查询轨迹</h2>
              <div className="mt-3 space-y-2 text-sm">{data.trace.map((item) => <div key={item.step} className="rounded bg-slate-50 p-2"><strong>{item.step}. {item.name}</strong><div className="text-gray-500">{item.records} records</div></div>)}</div>
            </section>
          </aside>

          <section className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="relative ml-3 border-l-2 border-cyan-200 pl-7">
              {visibleEvents.map((item, index) => (
                <article key={`${item.event_type}-${item.timestamp}-${index}`} className="relative mb-7 rounded-xl border bg-white p-5 shadow-sm">
                  <span className="absolute -left-[38px] top-6 h-5 w-5 rounded-full border-4 border-white bg-cyan-500 shadow" />
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-cyan-700">{item.event_type}</div>
                      <h2 className="mt-1 text-lg font-bold">{item.title}</h2>
                      {item.subtitle && <p className="text-sm text-gray-500">{item.subtitle}</p>}
                    </div>
                    <div className="text-right text-xs text-gray-500">
                      <div>{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'No timestamp'}</div>
                      <div className="mt-1 rounded bg-amber-50 px-2 py-1 text-amber-700">{item.date_semantics}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    {item.gene && <span className="rounded bg-violet-100 px-2 py-1 text-violet-800">{item.gene}</span>}
                    {item.source && <span className="rounded bg-slate-100 px-2 py-1">{item.source}</span>}
                  </div>
                  {item.actions.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{item.actions.map((action) => <button key={action.type} className="rounded border px-3 py-1.5 text-sm" onClick={() => executeAction(item, action.type)}>{action.label}</button>)}</div>}
                </article>
              ))}
              {visibleEvents.length === 0 && <div className="py-12 text-center text-gray-500">此筛选条件没有事件。</div>}
            </div>
          </section>
        </div>
      )}

      {data && <section className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{data.disclaimer}</section>}
    </main>
  )
}
