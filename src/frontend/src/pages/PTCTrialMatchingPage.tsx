import { useEffect, useMemo, useState } from 'react'

import { getPTCCase } from '../api/ptcResearch'
import { getPTCTrialMatches, type TrialMatchingResponse } from '../api/ptcTrialMatching'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'
import DualModeSelector from '../components/DualModeSelector'

export default function PTCTrialMatchingPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [advancedCaseId, setAdvancedCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [activeOnly, setActiveOnly] = useState(true)
  const [data, setData] = useState<TrialMatchingResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [advancedLoading, setAdvancedLoading] = useState(false)
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

  async function resolveAdvancedCase() {
    const requested = advancedCaseId.trim()
    if (!requested) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const item = await getPTCCase(requested)
      const normalized: PTCLatestCase = {
        case_id: item.case_id,
        source_dataset: item.source_dataset,
        source_project: item.source_project,
        disease: item.disease,
        sex: item.sex,
        age_range: item.age_range,
        pathologic_stage: item.pathologic_stage,
        t_status: item.t_status,
        n_status: item.n_status,
        m_status: item.m_status,
        vital_status: item.vital_status,
        days_to_last_follow_up: item.days_to_last_follow_up,
        days_to_death: item.days_to_death,
        variants: item.variants,
        outcomes: item.outcomes,
      }
      setCases((current) => current.some((value) => value.case_id === normalized.case_id) ? current : [normalized, ...current])
      setCaseId(normalized.case_id)
      setGene('')
      setData(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '找不到指定病例')
    } finally {
      setAdvancedLoading(false)
    }
  }

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
        <h1 className="text-3xl font-bold">PTC 研究候选试验导航</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          系统只计算研究相关度，不判断真实入组资格。年龄、Stage、性别、ECOG、器官功能、既往治疗与排除条件独立核验，且不会增加相关度分数。
        </p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <DualModeSelector
        title="选择研究病例"
        description="默认从数据库最近 100 笔选择；进阶模式可用完整 Case ID 查询整个数据库。"
        recentContent={(
          <div className="grid gap-4 p-5 md:grid-cols-4">
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
                {loading ? '比对中…' : '开始研究比对'}
              </button>
            </div>
          </div>
        )}
        advancedLabel="完整 Case ID"
        advancedPlaceholder="例如 TCGA-XX-XXXX"
        advancedValue={advancedCaseId}
        onAdvancedValueChange={setAdvancedCaseId}
        onAdvancedSubmit={resolveAdvancedCase}
        advancedLoading={advancedLoading}
        advancedHelp="精确查询只负责定位病例；试验结果仍使用同一套研究相关度与资格核验方法。"
      />

      {data && (
        <div className="mt-6 space-y-5">
          <section className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
            <strong>方法：</strong>{data.methodology.matching_version} · 相关度最高 {data.methodology.maximum_score} 分 ·
            资格与分数分离：是 · 资格判定：否
          </section>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <Metric label="试验总数" value={data.summary.total} />
            <Metric label="研究候选" value={data.summary.research_candidate} />
            <Metric label="相关资料不足" value={data.summary.insufficient_relevance_data} />
            <Metric label="低相关" value={data.summary.low_relevance} />
            <Metric label="资格冲突" value={data.summary.eligibility_conflict_detected} />
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
                    <div className="text-xs uppercase text-gray-500">研究相关度 · {classificationLabel(item.classification)}</div>
                    <div className="mt-1 text-xs font-semibold text-amber-700">{eligibilityLabel(item.eligibility_status)}</div>
                  </div>
                </div>

                <div className="grid gap-5 p-5 xl:grid-cols-2">
                  <CriterionGroup title="研究相关度评分" criteria={item.relevance_criteria} />
                  <CriterionGroup title="资格核验（不计分）" criteria={item.eligibility_criteria} />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t p-5 text-sm">
                  <div className="space-y-1">
                    <div><strong>相关度阻塞：</strong>{item.blocking_relevance_mismatches.join(', ') || '无明确阻塞'}</div>
                    <div><strong>资格冲突：</strong>{item.eligibility_conflicts.join(', ') || '无已解析冲突'}</div>
                    <div><strong>资格缺失／未核验：</strong>{item.missing_or_unverified_eligibility.join(', ') || '无'}</div>
                  </div>
                  {item.source_url && <a className="rounded border border-emerald-300 px-3 py-2 font-semibold text-emerald-700" href={item.source_url} target="_blank" rel="noreferrer">打开 ClinicalTrials.gov</a>}
                </div>
              </article>
            ))}
            {data.matches.length === 0 && <div className="rounded-xl border border-dashed bg-white p-12 text-center text-gray-500">没有符合当前筛选条件的已同步试验。</div>}
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <strong>真实资格仍需：</strong>{data.methodology.required_for_real_eligibility.join('、')}。<br />
            {data.disclaimer}
          </section>
        </div>
      )}
    </main>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div>
}

function CriterionGroup({ title, criteria }: { title: string; criteria: TrialMatchingResponse['matches'][number]['criteria'] }) {
  return <section><h3 className="font-bold">{title}</h3><div className="mt-3 grid gap-3">{criteria.map((criterion) => (
    <div key={criterion.name} className={`rounded border p-3 ${criterionClass(criterion.status)}`}>
      <div className="flex justify-between gap-3"><strong>{criterion.name}</strong><span>{criterion.track === 'relevance' ? `${criterion.awarded}/${criterion.weight}` : '不计分'}</span></div>
      <div className="mt-1 text-sm">{criterion.detail}</div>
    </div>
  ))}</div></section>
}

function criterionClass(status: 'match' | 'mismatch' | 'unknown'): string {
  if (status === 'match') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (status === 'mismatch') return 'border-red-200 bg-red-50 text-red-900'
  return 'border-amber-200 bg-amber-50 text-amber-900'
}

function classificationLabel(value: TrialMatchingResponse['matches'][number]['classification']): string {
  if (value === 'research_candidate') return 'research candidate'
  if (value === 'low_relevance') return 'low relevance'
  return 'insufficient relevance data'
}

function eligibilityLabel(value: TrialMatchingResponse['matches'][number]['eligibility_status']): string {
  if (value === 'conflict_detected') return '资格文本发现冲突，仍非最终判定'
  if (value === 'criteria_text_aligned_review_required') return '资格文本表面一致，仍需人工核验'
  return '资格资料不完整，需人工核验'
}
