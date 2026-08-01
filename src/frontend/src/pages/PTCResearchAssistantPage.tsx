import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import PTCResearchAssistant from '../components/PTCResearchAssistant'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCResearchAssistantPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await getLatestPTCCases(100)
        setCases(response.cases)
        const params = new URLSearchParams(window.location.search)
        const requestedCase = params.get('case')
        const requestedGene = params.get('gene')?.toUpperCase() || null
        const initial = response.cases.find((item) => item.case_id === requestedCase) || response.cases[0]
        setCaseId(initial?.case_id || '')
        setGene(requestedGene || initial?.variants[0]?.gene?.toUpperCase() || null)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '无法载入 PTC 研究病例')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const selectedCase = useMemo(() => cases.find((item) => item.case_id === caseId) || null, [cases, caseId])
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )
  const filteredCases = useMemo(() => {
    const needle = query.trim().toUpperCase()
    if (!needle) return cases
    return cases.filter((item) => {
      const genesText = item.variants.map((variant) => variant.gene).join(' ').toUpperCase()
      return item.case_id.toUpperCase().includes(needle)
        || (item.pathologic_stage || '').toUpperCase().includes(needle)
        || genesText.includes(needle)
    })
  }, [cases, query])

  function chooseCase(next: string) {
    setCaseId(next)
    const selected = cases.find((item) => item.case_id === next)
    setGene(selected?.variants[0]?.gene?.toUpperCase() || null)
    const url = new URL(window.location.href)
    url.searchParams.set('case', next)
    url.searchParams.delete('gene')
    window.history.replaceState({}, '', url)
  }

  function chooseGene(next: string | null) {
    setGene(next)
    const url = new URL(window.location.href)
    if (next) url.searchParams.set('gene', next)
    else url.searchParams.delete('gene')
    window.history.replaceState({}, '', url)
  }

  function openGeneIn3D(nextGene: string) {
    navigate(`/ptc-3d?case=${encodeURIComponent(caseId)}&gene=${encodeURIComponent(nextGene)}&view=protein`)
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">PTC Evidence-grounded Workspace</p>
        <h1 className="text-3xl font-bold text-gray-900">病例研究助手与可追溯问答</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          从最近下载的 100 个 TCGA-THCA 公开病例中选择研究对象。回答直接引用已同步的药物、CIViC／PubMed 证据、PMC 图表与临床试验，并保留完整查询轨迹。
        </p>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[340px_1fr]">
        <aside className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <div className="bg-slate-900 p-4 text-white">
            <div className="font-bold">选择研究病例</div>
            <input
              aria-label="搜索助手病例"
              className="mt-3 w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 text-sm"
              placeholder="病例号、Stage、BRAF、RET…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="mt-2 text-xs text-slate-400">{filteredCases.length} / {cases.length} 例</div>
          </div>
          <div className="max-h-[620px] overflow-y-auto">
            {loading && <div className="p-8 text-center text-gray-500">载入病例中…</div>}
            {!loading && filteredCases.map((item) => (
              <button
                key={item.case_id}
                className={`block w-full border-b px-4 py-3 text-left hover:bg-indigo-50 ${caseId === item.case_id ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-300' : ''}`}
                onClick={() => chooseCase(item.case_id)}
              >
                <div className="flex items-center justify-between gap-2">
                  <strong>{item.case_id}</strong>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{item.variants.length} variants</span>
                </div>
                <div className="mt-1 text-xs text-gray-500">{item.pathologic_stage || 'Stage 未提供'} · {item.vital_status || 'Outcome 未提供'}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {Array.from(new Set(item.variants.map((variant) => variant.gene))).slice(0, 6).map((itemGene) => (
                    <span key={itemGene} className="rounded bg-violet-50 px-2 py-0.5 text-[11px] text-violet-700">{itemGene}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </aside>

        <section className="space-y-5">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl font-bold">{caseId || '尚未选择病例'}</h2>
                <p className="text-sm text-gray-500">{selectedCase?.source_dataset || 'TCGA-THCA'} · {selectedCase?.pathologic_stage || 'Stage 未提供'}</p>
              </div>
              {caseId && gene && (
                <button className="rounded bg-violet-600 px-4 py-2 text-sm font-semibold text-white" onClick={() => openGeneIn3D(gene)}>
                  打开 {gene} 3D 全链
                </button>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                className={`rounded-full border px-3 py-1.5 text-sm ${gene === null ? 'border-indigo-500 bg-indigo-100 text-indigo-800' : 'border-gray-200'}`}
                onClick={() => chooseGene(null)}
              >
                自动选择
              </button>
              {genes.map((itemGene) => (
                <button
                  key={itemGene}
                  className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${gene === itemGene ? 'border-violet-500 bg-violet-100 text-violet-800' : 'border-gray-200 bg-white text-gray-700'}`}
                  onClick={() => chooseGene(itemGene)}
                >
                  {itemGene}
                </button>
              ))}
            </div>
          </div>

          <PTCResearchAssistant caseId={caseId || null} gene={gene} onOpenGene={openGeneIn3D} />

          <section className="rounded-xl border bg-amber-50 p-5 text-sm text-amber-900 shadow-sm">
            <h3 className="font-bold">研究使用边界</h3>
            <p className="mt-2 leading-6">
              本工作台只处理去识别化公开研究资料。回答是可核对的资料聚合，不是诊断、处方、剂量建议或真实患者治疗意见。任何临床应用必须由合格医疗团队独立审查。
            </p>
          </section>
        </section>
      </div>
    </main>
  )
}
