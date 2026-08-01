import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DualModeSelector from '../components/DualModeSelector'
import PTCResearchAssistant from '../components/PTCResearchAssistant'
import { getPTCCase } from '../api/ptcResearch'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCResearchAssistantPage() {
  const navigate = useNavigate()
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [advancedCase, setAdvancedCase] = useState<PTCLatestCase | null>(null)
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState<string | null>(null)
  const [exactCaseId, setExactCaseId] = useState('')
  const [loading, setLoading] = useState(true)
  const [advancedLoading, setAdvancedLoading] = useState(false)
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
        setError(reason instanceof Error ? reason.message : '無法載入 PTC 研究病例')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const selectedCase = useMemo(
    () => advancedCase?.case_id === caseId ? advancedCase : cases.find((item) => item.case_id === caseId) || null,
    [advancedCase, cases, caseId],
  )
  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  function chooseCase(next: string) {
    setAdvancedCase(null)
    setCaseId(next)
    const selected = cases.find((item) => item.case_id === next)
    setGene(selected?.variants[0]?.gene?.toUpperCase() || null)
    syncUrl(next, null)
  }

  async function queryExactCase() {
    const normalized = exactCaseId.trim()
    if (!normalized) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const record = await getPTCCase(normalized)
      const converted = record as PTCLatestCase
      setAdvancedCase(converted)
      setCaseId(converted.case_id)
      const firstGene = converted.variants[0]?.gene?.toUpperCase() || null
      setGene(firstGene)
      syncUrl(converted.case_id, firstGene)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '資料庫找不到指定病例')
    } finally {
      setAdvancedLoading(false)
    }
  }

  function chooseGene(next: string | null) {
    setGene(next)
    syncUrl(caseId, next)
  }

  function syncUrl(nextCase: string, nextGene: string | null) {
    const url = new URL(window.location.href)
    if (nextCase) url.searchParams.set('case', nextCase)
    else url.searchParams.delete('case')
    if (nextGene) url.searchParams.set('gene', nextGene)
    else url.searchParams.delete('gene')
    window.history.replaceState({}, '', url)
  }

  function openGeneIn3D(nextGene: string) {
    navigate(`/ptc-3d?case=${encodeURIComponent(caseId)}&gene=${encodeURIComponent(nextGene)}&view=protein`)
  }

  const recentContent = (
    <div className="max-h-[680px] overflow-y-auto">
      {loading && <div className="p-8 text-center text-gray-500">載入病例中…</div>}
      {!loading && cases.map((item) => (
        <button
          key={item.case_id}
          className={`block w-full border-b px-4 py-3 text-left hover:bg-indigo-50 ${caseId === item.case_id && !advancedCase ? 'bg-indigo-50 ring-1 ring-inset ring-indigo-300' : ''}`}
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
      {!loading && cases.length === 0 && <div className="p-8 text-center text-gray-500">資料庫尚無可展示病例。</div>}
    </div>
  )

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">PTC Evidence-grounded Workspace</p>
        <h1 className="text-3xl font-bold text-gray-900">病例研究助手與可追溯主題分析</h1>
        <p className="mt-2 max-w-5xl text-gray-600">
          一般模式列出資料庫最近 100 個公開病例；進階模式可用完整 Case ID 精準查詢整個資料庫。選中病例後，再選擇該病例實際存在的基因與研究主題。
        </p>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[360px_1fr]">
        <DualModeSelector
          title="選擇研究病例"
          description="預設列出最近 100 筆；已知 Case ID 時可切換進階查詢。"
          recentContent={recentContent}
          advancedLabel="完整 Case ID"
          advancedPlaceholder="例如 TCGA-XX-YYYY"
          advancedValue={exactCaseId}
          onAdvancedValueChange={setExactCaseId}
          onAdvancedSubmit={queryExactCase}
          advancedLoading={advancedLoading}
          advancedHelp="進階模式會查詢整個資料庫，不受最近 100 筆限制；查詢結果仍需由後端確認存在。"
        />

        <section className="space-y-5">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl font-bold">{caseId || '尚未選擇病例'}</h2>
                <p className="text-sm text-gray-500">{selectedCase?.source_dataset || 'TCGA-THCA'} · {selectedCase?.pathologic_stage || 'Stage 未提供'}</p>
                {advancedCase && <p className="mt-1 text-xs font-semibold text-indigo-600">進階精準查詢結果</p>}
              </div>
              {caseId && gene && (
                <button className="rounded bg-violet-600 px-4 py-2 text-sm font-semibold text-white" onClick={() => openGeneIn3D(gene)}>
                  打開 {gene} 3D 全鏈
                </button>
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                className={`rounded-full border px-3 py-1.5 text-sm ${gene === null ? 'border-indigo-500 bg-indigo-100 text-indigo-800' : 'border-gray-200'}`}
                onClick={() => chooseGene(null)}
              >
                全部基因
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
            <h3 className="font-bold">研究使用邊界</h3>
            <p className="mt-2 leading-6">本工作台只處理去識別化公開研究資料。結果不是診斷、處方、劑量建議或真實患者治療意見。</p>
          </section>
        </section>
      </div>
    </main>
  )
}
