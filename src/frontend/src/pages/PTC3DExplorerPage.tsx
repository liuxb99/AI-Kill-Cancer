import { useEffect, useMemo, useRef, useState } from 'react'

import PTCCell3D from '../components/PTCCell3D'
import PTCLiteratureAssetsPanel from '../components/PTCLiteratureAssetsPanel'
import PTCProtein3D from '../components/PTCProtein3D'
import PTCTargetingPanel from '../components/PTCTargetingPanel'
import {
  getLatestPTCCases,
  getPTCProteinStructure,
  type PTCLatestCase,
  type PTCProteinStructure,
} from '../api/ptcVisualization'

type ExplorerView = 'cell' | 'protein' | 'targeting' | 'literature'

function parseExplorerView(value: string | null): ExplorerView {
  if (value === 'protein' || value === 'targeting' || value === 'literature') return value
  return 'cell'
}

function updateExplorerUrl(caseId?: string, gene?: string, view?: ExplorerView) {
  const url = new URL(window.location.href)
  if (caseId) url.searchParams.set('case', caseId)
  else url.searchParams.delete('case')
  if (gene) url.searchParams.set('gene', gene)
  else url.searchParams.delete('gene')
  if (view) url.searchParams.set('view', view)
  else url.searchParams.delete('view')
  window.history.replaceState({}, '', url)
}

export default function PTC3DExplorerPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [selectedCase, setSelectedCase] = useState<PTCLatestCase | null>(null)
  const [selectedGene, setSelectedGene] = useState<string | null>(null)
  const [protein, setProtein] = useState<PTCProteinStructure | null>(null)
  const [view, setView] = useState<ExplorerView>('cell')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [proteinLoading, setProteinLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const targetingRef = useRef<HTMLDivElement>(null)
  const literatureRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await getLatestPTCCases(100)
        setCases(result.cases)
        const params = new URLSearchParams(window.location.search)
        const caseId = params.get('case')
        const requestedGene = params.get('gene')?.toUpperCase() || null
        const requestedView = parseExplorerView(params.get('view'))
        const initialCase = result.cases.find((item) => item.case_id === caseId) || result.cases[0] || null
        setSelectedCase(initialCase)
        setSelectedGene(requestedGene)
        setView(requestedView)

        if (initialCase && requestedGene && requestedView === 'protein') {
          setProteinLoading(true)
          try {
            setProtein(await getPTCProteinStructure(requestedGene))
          } catch (reason) {
            setProtein(null)
            setError(reason instanceof Error ? reason.message : `${requestedGene} 尚無可用結構映射`)
          } finally {
            setProteinLoading(false)
          }
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '無法載入最近 100 個 PTC 病例')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  useEffect(() => {
    if (loading) return
    if (view === 'targeting') targetingRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    if (view === 'literature') literatureRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [view, loading, selectedGene])

  const genes = useMemo(
    () => Array.from(new Set((selectedCase?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selectedCase],
  )

  const selectedGeneVariants = useMemo(
    () => (selectedCase?.variants || []).filter((item) => item.gene.toUpperCase() === selectedGene?.toUpperCase()),
    [selectedCase, selectedGene],
  )

  const filteredCases = useMemo(() => {
    const normalized = query.trim().toUpperCase()
    if (!normalized) return cases
    return cases.filter((item) => {
      const genesText = item.variants.map((variant) => variant.gene).join(' ').toUpperCase()
      return item.case_id.toUpperCase().includes(normalized)
        || (item.pathologic_stage || '').toUpperCase().includes(normalized)
        || (item.vital_status || '').toUpperCase().includes(normalized)
        || genesText.includes(normalized)
    })
  }, [cases, query])

  async function selectGene(gene: string, nextView: ExplorerView = 'protein') {
    const normalized = gene.toUpperCase()
    setSelectedGene(normalized)
    setError(null)
    setView(nextView)
    updateExplorerUrl(selectedCase?.case_id, normalized, nextView)

    if (nextView !== 'protein') return
    setProteinLoading(true)
    try {
      setProtein(await getPTCProteinStructure(normalized))
    } catch (reason) {
      setProtein(null)
      setError(reason instanceof Error ? reason.message : `${normalized} 尚無可用結構映射`)
    } finally {
      setProteinLoading(false)
    }
  }

  function chooseCase(item: PTCLatestCase) {
    setSelectedCase(item)
    setSelectedGene(null)
    setProtein(null)
    setView('cell')
    updateExplorerUrl(item.case_id, undefined, 'cell')
  }

  async function switchView(next: ExplorerView) {
    const gene = next === 'cell' ? undefined : selectedGene || genes[0]
    if (gene && gene !== selectedGene) setSelectedGene(gene)
    setView(next)
    updateExplorerUrl(selectedCase?.case_id, gene, next)

    if (next === 'protein' && gene) {
      setProteinLoading(true)
      setError(null)
      try {
        setProtein(await getPTCProteinStructure(gene))
      } catch (reason) {
        setProtein(null)
        setError(reason instanceof Error ? reason.message : `${gene} 尚無可用結構映射`)
      } finally {
        setProteinLoading(false)
      }
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setError('瀏覽器不允許複製連結，請從網址列手動複製。')
    }
  }

  return (
    <main className="mx-auto max-w-[1600px] px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-cyan-600">PTC Multi-scale 3D Explorer</p>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">癌細胞、蛋白質與靶向治療多尺度 3D</h1>
            <p className="mt-2 max-w-5xl text-gray-600">
              從最近 100 個 TCGA-THCA 公開研究病例進入癌細胞尺度，再深入蛋白結構、突變殘基、訊號路徑、藥物、證據、臨床試驗與 PMC 開放全文圖表。
            </p>
          </div>
          <button className="rounded border border-cyan-300 bg-white px-4 py-2 text-sm font-semibold text-cyan-700 hover:bg-cyan-50" onClick={() => void copyLink()}>
            {copied ? '連結已複製' : '複製目前視圖連結'}
          </button>
        </div>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[350px_1fr]">
        <aside className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <div className="border-b bg-slate-900 px-4 py-3 text-white">
            <div className="font-bold">最近 100 個病例</div>
            <div className="text-xs text-slate-300">依入庫更新時間排序</div>
            <input
              aria-label="搜尋最近 PTC 病例"
              className="mt-3 w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-400"
              placeholder="病例號、Stage、BRAF、RET…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="mt-2 text-[11px] text-slate-400">顯示 {filteredCases.length} / {cases.length} 例</div>
          </div>
          <div className="max-h-[860px] overflow-y-auto">
            {loading && <div className="p-8 text-center text-gray-500">載入中…</div>}
            {!loading && filteredCases.map((item) => {
              const originalIndex = cases.findIndex((candidate) => candidate.case_id === item.case_id)
              return (
                <button
                  key={`${item.source_dataset}:${item.case_id}`}
                  className={`block w-full border-b px-4 py-3 text-left transition hover:bg-cyan-50 ${selectedCase?.case_id === item.case_id ? 'bg-cyan-50 ring-1 ring-inset ring-cyan-300' : ''}`}
                  onClick={() => chooseCase(item)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-gray-900">{originalIndex + 1}. {item.case_id}</span>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{item.variants.length} variants</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{item.pathologic_stage || 'Stage 未提供'} · {item.vital_status || 'Outcome 未提供'}</div>
                </button>
              )
            })}
            {!loading && filteredCases.length === 0 && <div className="p-8 text-center text-gray-500">資料庫目前沒有符合條件的病例。</div>}
          </div>
        </aside>

        <section className="space-y-5">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold">{selectedCase?.case_id || '請選擇病例'}</h2>
                <p className="text-sm text-gray-500">{selectedCase?.source_dataset || 'TCGA-THCA'}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <ViewButton active={view === 'cell'} onClick={() => void switchView('cell')}>癌細胞 3D</ViewButton>
                <ViewButton active={view === 'protein'} onClick={() => void switchView('protein')}>蛋白折疊 3D</ViewButton>
                <ViewButton active={view === 'targeting'} onClick={() => void switchView('targeting')}>靶向鏈</ViewButton>
                <ViewButton active={view === 'literature'} onClick={() => void switchView('literature')}>文獻圖表</ViewButton>
              </div>
            </div>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
              <Info label="病理分期" value={selectedCase?.pathologic_stage} />
              <Info label="TNM" value={[selectedCase?.t_status, selectedCase?.n_status, selectedCase?.m_status].filter(Boolean).join(' / ')} />
              <Info label="性別" value={selectedCase?.sex} />
              <Info label="年齡區間" value={selectedCase?.age_range} />
              <Info label="生存狀態" value={selectedCase?.vital_status} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {genes.map((gene) => (
                <button
                  key={gene}
                  className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${selectedGene === gene ? 'border-violet-500 bg-violet-100 text-violet-800' : 'border-gray-200 bg-white text-gray-700 hover:border-violet-300 hover:bg-violet-50'}`}
                  onClick={() => void selectGene(gene, view === 'cell' ? 'protein' : view)}
                >
                  {gene}
                </button>
              ))}
              {selectedCase && genes.length === 0 && <span className="text-sm text-gray-500">此病例尚無已匯入基因變異。</span>}
            </div>
          </div>

          {view === 'cell' && <PTCCell3D selectedCase={selectedCase} onSelectGene={(gene) => void selectGene(gene)} />}
          {view === 'protein' && <PTCProtein3D structure={protein} variants={selectedGeneVariants} loading={proteinLoading} />}

          <div ref={targetingRef} className={`scroll-mt-5 rounded-xl ${view === 'targeting' ? 'ring-2 ring-indigo-400 ring-offset-2' : ''}`}>
            <PTCTargetingPanel gene={selectedGene} proteinChange={selectedGeneVariants[0]?.protein_change} />
          </div>
          <div ref={literatureRef} className={`scroll-mt-5 rounded-xl ${view === 'literature' ? 'ring-2 ring-emerald-400 ring-offset-2' : ''}`}>
            <PTCLiteratureAssetsPanel gene={selectedGene} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h3 className="font-bold">病例變異明細</h3>
              <div className="mt-3 max-h-80 overflow-auto">
                {(selectedCase?.variants || []).map((variant) => (
                  <button key={variant.variant_id} className="flex w-full items-center justify-between gap-3 border-b py-2 text-left text-sm hover:bg-gray-50" onClick={() => void selectGene(variant.gene)}>
                    <span><strong>{variant.gene}</strong> · {variant.protein_change || variant.variant_id}</span>
                    <span className="text-xs text-gray-500">{variant.classification || '未分類'}</span>
                  </button>
                ))}
                {!selectedCase?.variants.length && <div className="py-6 text-sm text-gray-500">尚無變異資料。</div>}
              </div>
            </section>
            <section className="rounded-xl border bg-amber-50 p-5 shadow-sm">
              <h3 className="font-bold text-amber-900">結構與治療解釋邊界</h3>
              <p className="mt-2 text-sm leading-6 text-amber-900/80">
                TCGA 提供去識別化病例、病理與分子變異，不包含患者癌細胞的完整顯微或原子結構。細胞層為科學示意，蛋白層使用公開參考座標；藥物、證據與試驗僅供研究探索。
              </p>
            </section>
          </div>
        </section>
      </div>
    </main>
  )
}

function ViewButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button className={`rounded px-4 py-2 text-sm font-semibold ${active ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700'}`} onClick={onClick}>{children}</button>
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="font-semibold text-gray-900">{value || '—'}</div></div>
}
