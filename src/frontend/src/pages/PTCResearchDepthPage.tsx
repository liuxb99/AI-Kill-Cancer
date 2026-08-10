import { useEffect, useMemo, useState } from 'react'

import {
  getResearchDepthPacket,
  listResearchEvents,
  listResearchHypotheses,
  runResearchDepthLoop,
  type ResearchDepthPacket,
  type ResearchEvent,
  type ResearchHypothesis,
  type ResearchLoopResult,
} from '../api/ptcResearchDepth'

export default function PTCResearchDepthPage() {
  const [gene, setGene] = useState('BRAF')
  const [proteinChange, setProteinChange] = useState('p.V600E')
  const [packet, setPacket] = useState<ResearchDepthPacket | null>(null)
  const [run, setRun] = useState<ResearchLoopResult | null>(null)
  const [hypotheses, setHypotheses] = useState<ResearchHypothesis[]>([])
  const [events, setEvents] = useState<ResearchEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const normalizedGene = useMemo(() => gene.trim().toUpperCase(), [gene])

  async function load() {
    if (!normalizedGene) return
    setLoading(true)
    setError(null)
    try {
      const [nextPacket, hypothesisResult, eventResult] = await Promise.all([
        getResearchDepthPacket(normalizedGene, proteinChange.trim() || undefined),
        listResearchHypotheses(normalizedGene),
        listResearchEvents(normalizedGene),
      ])
      setPacket(nextPacket)
      setHypotheses(hypothesisResult.items)
      setEvents(eventResult.events)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入研究深度分析')
    } finally {
      setLoading(false)
    }
  }

  async function runLoop() {
    if (!normalizedGene) return
    setLoading(true)
    setError(null)
    try {
      const result = await runResearchDepthLoop(normalizedGene, proteinChange.trim() || undefined)
      setRun(result)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '研究循環執行失敗')
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // Initial research target is intentionally fixed to the default fields.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <section>
        <p className="text-sm font-semibold text-primary-600">Research-Only AI Cancer Research Loop</p>
        <h1 className="text-3xl font-bold text-gray-900">PTC 研究深度工作台</h1>
        <p className="mt-2 max-w-4xl text-gray-600">
          將 outcome-blind cohort 分層、post-selection outcome feedback、evidence conflict、可反駁假說與 research digital thread 串成同一條可追溯研究流程。
        </p>
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Research only：所有 cohort association 都是描述性訊號；假說分數不是預後、因果推論、診斷或治療建議。
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
          <label className="text-sm">
            <span className="mb-1 block text-gray-600">Gene</span>
            <input
              aria-label="Research gene"
              className="w-full rounded border px-3 py-2"
              value={gene}
              onChange={(event) => setGene(event.target.value.toUpperCase())}
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-gray-600">Protein change（optional）</span>
            <input
              aria-label="Protein change"
              className="w-full rounded border px-3 py-2"
              value={proteinChange}
              onChange={(event) => setProteinChange(event.target.value)}
            />
          </label>
          <button
            className="self-end rounded border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            disabled={loading || !normalizedGene}
            onClick={() => void load()}
          >
            Refresh analysis
          </button>
          <button
            className="self-end rounded bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            disabled={loading || !normalizedGene}
            onClick={() => void runLoop()}
          >
            Run research loop
          </button>
        </div>
        {error && <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        {run && (
          <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            Run {run.reused ? 'reused unchanged inputs' : 'persisted'} · fingerprint {run.input_fingerprint.slice(0, 12)}… · {run.hypotheses.length} hypotheses
          </div>
        )}
      </section>

      {loading && !packet ? <div className="rounded border bg-white p-8 text-center text-gray-500">載入研究資料…</div> : null}

      {packet && (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            <Metric label="Research cases" value={packet.cohort_stratification.total_cases} />
            <Metric label="Biomarker positive" value={packet.cohort_stratification.positive.cases} />
            <Metric label="Evidence records" value={packet.evidence_conflict.total} />
            <Metric label="Conflict severity" value={packet.evidence_conflict.conflict_severity} />
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-lg border bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold">Cohort stratification</h2>
              <p className="mt-1 text-sm text-gray-500">Selection 不使用 outcome；outcome 只在分組完成後描述。</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <CohortCard title="Biomarker positive" group={packet.cohort_stratification.positive} />
                <CohortCard title="Biomarker negative" group={packet.cohort_stratification.negative} />
              </div>
              {packet.cohort_stratification.small_sample_warning && (
                <div className="mt-3 rounded bg-amber-50 p-2 text-xs text-amber-800">Small-sample warning：至少一組少於 20 cases。</div>
              )}
            </div>

            <div className="rounded-lg border bg-white p-5 shadow-sm">
              <h2 className="text-lg font-bold">Evidence conflict</h2>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <Info label="Supporting" value={packet.evidence_conflict.counts.supporting ?? 0} />
                <Info label="Conflicting" value={packet.evidence_conflict.counts.conflicting ?? 0} />
                <Info label="Weighted support" value={packet.evidence_conflict.weighted_support} />
                <Info label="Weighted conflict" value={packet.evidence_conflict.weighted_conflict} />
                <Info label="Source diversity" value={packet.evidence_conflict.source_diversity} />
                <Info label="Majority only" value={packet.evidence_conflict.majority_vote_only ? 'YES' : 'NO'} />
              </div>
              <div className="mt-4 space-y-2">
                {packet.evidence_conflict.unresolved_reasons.map((reason) => (
                  <div key={reason} className="rounded bg-gray-50 px-3 py-2 text-sm text-gray-700">{reason}</div>
                ))}
                {packet.evidence_conflict.unresolved_reasons.length === 0 && <div className="text-sm text-gray-500">No unresolved conflict flag.</div>}
              </div>
            </div>
          </section>
        </>
      )}

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold">Versioned hypotheses</h2>
            <p className="text-sm text-gray-500">每個假說都必須包含 falsification criteria、uncertainty 與 next data needed。</p>
          </div>
          <span className="rounded bg-indigo-50 px-3 py-1 text-sm text-indigo-700">{hypotheses.length}</span>
        </div>
        <div className="mt-4 space-y-4">
          {hypotheses.map((item) => (
            <article key={`${item.hypothesis_key ?? item.claim}:${item.version ?? 0}`} className="rounded border p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                <span className="rounded bg-gray-100 px-2 py-1">{item.hypothesis_type}</span>
                {item.version && <span>v{item.version}</span>}
                <span>clinical_use=false</span>
              </div>
              <h3 className="mt-2 font-semibold text-gray-900">{item.claim}</h3>
              <div className="mt-3 grid gap-3 md:grid-cols-2 text-sm">
                <div><div className="font-semibold text-gray-600">Falsification</div><p className="mt-1 text-gray-700">{item.falsification_criteria}</p></div>
                <div><div className="font-semibold text-gray-600">Next data needed</div><ul className="mt-1 list-disc pl-5 text-gray-700">{item.next_data_needed.map((entry) => <li key={entry}>{entry}</li>)}</ul></div>
              </div>
            </article>
          ))}
          {hypotheses.length === 0 && <div className="text-sm text-gray-500">尚未持久化研究假說；可執行 Research loop。</div>}
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Research digital thread</h2>
          <span className="text-sm text-gray-500">{events.length} events</span>
        </div>
        <div className="mt-4 space-y-3">
          {events.slice(0, 50).map((event) => (
            <div key={event.event_key} className="rounded border px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{event.event_type}</span>
                <span className="text-xs text-gray-500">{event.observed_at || '—'} · {event.date_semantics}</span>
              </div>
              <div className="mt-1 text-xs text-gray-500">source={event.source_type} · provenance preserved</div>
            </div>
          ))}
          {events.length === 0 && <div className="text-sm text-gray-500">尚未建立 research-loop event。</div>}
        </div>
      </section>
    </main>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-lg border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div>
}

function Info({ label, value }: { label: string; value: string | number }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="font-medium text-gray-900">{value}</div></div>
}

function CohortCard({ title, group }: { title: string; group: ResearchDepthPacket['cohort_stratification']['positive'] }) {
  const firstOutcome = group.outcome_feedback.outcomes[0]
  return (
    <div className="rounded border p-3 text-sm">
      <div className="font-semibold">{title}</div>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <Info label="Cases" value={group.cases} />
        <Info label="Fraction" value={`${Math.round(group.fraction * 100)}%`} />
        <Info label="Outcome coverage" value={`${Math.round(group.outcome_feedback.outcome_coverage * 100)}%`} />
        <Info label="Event proportion" value={firstOutcome?.event_proportion == null ? '—' : `${Math.round(firstOutcome.event_proportion * 100)}%`} />
      </div>
    </div>
  )
}
