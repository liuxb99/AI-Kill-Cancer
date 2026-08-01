import { useMemo, useState } from 'react'

import { askPTCAssistant, type PTCAssistantResponse } from '../api/ptcAssistant'

interface Props {
  caseId: string | null
  gene: string | null
  onOpenGene?: (gene: string) => void
}

const QUICK_QUESTIONS = [
  '为什么这个病例要关注当前突变？',
  '有哪些相关药物与证据？',
  '有哪些相关临床试验？',
  '有哪些论文图表支持这个研究方向？',
]

export default function PTCResearchAssistant({ caseId, gene, onOpenGene }: Props) {
  const [selectedQuestion, setSelectedQuestion] = useState(QUICK_QUESTIONS[0])
  const [result, setResult] = useState<PTCAssistantResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedEvidence, setExpandedEvidence] = useState<string | null>(null)

  const summary = useMemo(() => {
    if (!result) return null
    return `${result.case_facts.variants.length} variants · ${result.therapies.length} therapies · ${result.evidence.length} evidence · ${result.trials.length} trials`
  }, [result])

  async function submit(question: string) {
    if (!caseId) return
    setSelectedQuestion(question)
    setLoading(true)
    setError(null)
    try {
      setResult(await askPTCAssistant(caseId, question, gene))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成可追溯研究回答')
    } finally {
      setLoading(false)
    }
  }

  function runAction(action: PTCAssistantResponse['actions'][number]) {
    if ((action.type === 'open_3d' || action.type === 'open_targeting' || action.type === 'open_literature') && action.gene) {
      onOpenGene?.(action.gene)
      document.getElementById(
        action.type === 'open_literature' ? 'ptc-literature-assets' : 'ptc-protein-targeting',
      )?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    if (action.url) window.open(action.url, '_blank', 'noopener,noreferrer')
  }

  return (
    <section className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Evidence-grounded Research Assistant</p>
          <h3 className="text-xl font-bold text-gray-900">病例研究主题与证据追踪</h3>
          <p className="mt-1 text-sm text-gray-600">
            先从数据库病例与基因清单选择对象，再选择预设研究主题。系统不要求输入查询文字，也不调用外部 LLM。
          </p>
        </div>
        <div className="rounded bg-white px-3 py-2 text-xs text-gray-500 shadow-sm">
          {caseId || '尚未选择病例'}{gene ? ` · ${gene}` : ''}
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {QUICK_QUESTIONS.map((item) => (
          <button
            key={item}
            className={`rounded-lg border px-4 py-3 text-left text-sm font-semibold transition ${selectedQuestion === item ? 'border-indigo-500 bg-indigo-100 text-indigo-900' : 'border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-50'}`}
            disabled={!caseId || loading}
            onClick={() => void submit(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {!result && caseId && (
        <div className="mt-4 rounded border border-dashed border-indigo-200 bg-white p-5 text-center text-sm text-gray-500">
          从上方四个研究主题中选择一个，系统会直接整理当前病例的数据库证据。
        </div>
      )}

      {loading && <div className="mt-4 rounded bg-indigo-100 p-3 text-sm text-indigo-800">正在整理数据库证据…</div>}
      {error && <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {result && (
        <div className="mt-5 space-y-4">
          <div className="rounded-lg border border-indigo-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="font-bold text-gray-900">研究回答</h4>
              <span className="text-xs text-gray-500">{summary}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-gray-700">{result.answer}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {result.actions.map((action) => (
              <button
                key={`${action.type}:${action.label}`}
                className="rounded border border-indigo-300 bg-white px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
                onClick={() => runAction(action)}
              >
                {action.label}
              </button>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <div className="rounded border bg-white p-4">
              <h4 className="font-bold">病例事实</h4>
              <dl className="mt-2 space-y-2 text-sm">
                <Fact label="Dataset" value={result.case_facts.source_dataset} />
                <Fact label="Stage" value={result.case_facts.pathologic_stage} />
                <Fact label="Vital status" value={result.case_facts.vital_status} />
                <Fact label="Genes" value={result.case_facts.genes.join(', ')} />
              </dl>
            </div>
            <div className="rounded border bg-white p-4">
              <h4 className="font-bold">候选研究治疗</h4>
              <div className="mt-2 space-y-2 text-sm">
                {result.therapies.slice(0, 6).map((item) => (
                  <article key={item.therapy_key} className="rounded bg-slate-50 p-2">
                    <div className="font-semibold">{item.name}</div>
                    <div className="text-xs text-gray-500">{item.approval_status || item.source}</div>
                  </article>
                ))}
                {result.therapies.length === 0 && <p className="text-gray-500">尚无持久化药物记录。</p>}
              </div>
            </div>
            <div className="rounded border bg-white p-4">
              <h4 className="font-bold">计算轨迹</h4>
              <ol className="mt-2 space-y-2 text-sm">
                {result.trace.map((step) => (
                  <li key={step.step} className="flex items-center justify-between gap-3">
                    <span>{step.step}. {step.name}</span>
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">{step.records}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          <div>
            <h4 className="font-bold text-gray-900">可核对证据</h4>
            <div className="mt-2 space-y-2">
              {result.evidence.map((item) => (
                <article key={item.evidence_key} className="rounded border bg-white p-3 text-sm">
                  <button
                    className="flex w-full items-start justify-between gap-4 text-left"
                    onClick={() => setExpandedEvidence(expandedEvidence === item.evidence_key ? null : item.evidence_key)}
                  >
                    <span>
                      <strong>{item.title || item.evidence_key}</strong>
                      <span className="ml-2 text-xs text-gray-500">{item.level || 'ungraded'} · {item.source}</span>
                    </span>
                    <span className="text-indigo-600">{expandedEvidence === item.evidence_key ? '收起' : '展开'}</span>
                  </button>
                  {expandedEvidence === item.evidence_key && (
                    <div className="mt-3 border-t pt-3">
                      {item.summary && <p className="leading-6 text-gray-600">{item.summary}</p>}
                      <div className="mt-2 text-xs text-gray-500">
                        {item.publication_id ? `PMID ${item.publication_id}` : item.source}
                        {item.figures.length > 0 ? ` · ${item.figures.length} figures` : ''}
                        {item.tables.length > 0 ? ` · ${item.tables.length} tables` : ''}
                      </div>
                      {item.url && <a className="mt-2 inline-block text-indigo-600 underline" href={item.url} target="_blank" rel="noreferrer">打开来源</a>}
                    </div>
                  )}
                </article>
              ))}
              {result.evidence.length === 0 && <p className="text-sm text-gray-500">尚无可引用证据。</p>}
            </div>
          </div>

          <p className="border-t pt-3 text-xs text-amber-700">{result.disclaimer}</p>
        </div>
      )}
    </section>
  )
}

function Fact({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-right font-semibold text-gray-900">{value || '—'}</dd>
    </div>
  )
}
