import { useEffect, useMemo, useState } from 'react'

import PTCCell3D from '../components/PTCCell3D'
import PTCProtein3D from '../components/PTCProtein3D'
import {
  getLatestPTCCases,
  getPTCProteinStructure,
  type PTCLatestCase,
  type PTCProteinStructure,
} from '../api/ptcVisualization'

function updateExplorerUrl(caseId?: string, gene?: string, view?: 'cell' | 'protein') {
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
  const [view, setView] = useState<'cell' | 'protein'>('cell')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [proteinLoading, setProteinLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
        const requestedView = params.get('view') === 'protein' ? 'protein' : 'cell'
        const initialCase = result.cases.find((item) => item.case_id === caseId) || result.cases[0] || null
        setSelectedCase(initialCase)
        setView(requestedView)
        if (initialCase && requestedGene) {
          setSelectedGene(requestedGene)
          setProteinLoading(true)
          try {
            setProtein(await getPTCProteinStructure(requestedGene))
          } catch {
            setProtein(null)
            setView('cell')
          } finally {
            setProteinLoading(false)
          }
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '无法载入最近 100 个 PTC 病例')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

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

  async function selectGene(gene: string) {
    const normalized = gene.toUpperCase()
    setSelectedGene(normalized)
    setProteinLoading(true)
    setError(null)
    setView('protein')
    updateExplorerUrl(selectedCase?.case_id, normalized, 'protein')
    try {
      setProtein(await getPTCProteinStructure(normalized))
    } catch (reason) {
      setProtein(null)
      setError(reason instanceof Error ? reason.message : `${normalized} 尚无可用结构映射`)
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

  function switchView(next: 'cell' | 'protein') {
    setView(next)
    updateExplorerUrl(selectedCase?.case_id, next === 'protein' ? selectedGene || undefined : undefined, next)
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setError('浏览器不允许复制链接，请从地址栏手动复制。')
    }
  }

  return (
    <main className="mx-auto max-w-[1600px] px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-cyan-600">PTC Multi-scale 3D Explorer</p>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">癌细胞与蛋白质多尺度 3D 展示</h1>
            <p className="mt-2 max-w-5xl text-gray-600">
              从最近下载的 100 个 TCGA-THCA 公开研究病例进入癌细胞尺度，再深入到 BRAF、RET、NTRK、TERT、RAS 等蛋白结构。
              癌细胞为依据病例突变资料生成的科学示意模型；蛋白结构来自 AlphaFold DB 预测与 PDB 实验结构。
            </p>
          </div>
          <button className="rounded border border-cyan-300 bg-white px-4 py-2 text-sm font-semibold text-cyan-700 hover:bg-cyan-50" onClick={() => void copyLink()}>
            {copied ? '链接已复制' : '复制当前 3D 视图链接'}
          </button>
        </div>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[350px_1fr]">
        <aside className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <div className="border-b bg-slate-900 px-4 py-3 text-white">
            <div className="font-bold">最近下载病例</div>
            <div className="text-xs text-slate-300">按入库更新时间排序 · 最多 100 例</div>
            <input
              aria-label="搜索最近 PTC 病例"
              className="mt-3 w-full rounded border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-400"
              placeholder="病例号、Stage、BRAF、RET…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <div className="mt-2 text-[11px] text-slate-400">显示 {filteredCases.length} / {cases.length} 例</div>
          </div>
          <div className="max-h-[860px] overflow-y-auto">
            {loading && <div className="p-8 text-center text-gray-500">载入中…</div>}
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
                  <div className="mt-1 truncate text-[11px] text-gray-400">{item.updated_at ? `更新 ${new Date(item.updated_at).toLocaleString()}` : item.source_dataset}</div>
                </button>
              )
            })}
            {!loading && filteredCases.length === 0 && (
              <div className="p-8 text-center text-gray-500">{cases.length === 0 ? '尚未下载病例，请先在 PTC 总控台执行同步。' : '没有符合搜索条件的病例。'}</div>
            )}
          </div>
        </aside>

        <section className="space-y-5">
          <div className="rounded-xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold">{selectedCase?.case_id || '请选择病例'}</h2>
                <p className="text-sm text-gray-500">{selectedCase?.source_dataset || 'TCGA-THCA'}</p>
              </div>
              <div className="flex gap-2">
                <button className={`rounded px-4 py-2 text-sm font-semibold ${view === 'cell' ? 'bg-cyan-600 text-white' : 'bg-gray-100 text-gray-700'}`} onClick={() => switchView('cell')}>癌细胞 3D</button>
                <button className={`rounded px-4 py-2 text-sm font-semibold ${view === 'protein' ? 'bg-violet-600 text-white' : 'bg-gray-100 text-gray-700'}`} onClick={() => switchView('protein')}>蛋白折叠 3D</button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
              <Info label="病理分期" value={selectedCase?.pathologic_stage} />
              <Info label="TNM" value={[selectedCase?.t_status, selectedCase?.n_status, selectedCase?.m_status].filter(Boolean).join(' / ')} />
              <Info label="性别" value={selectedCase?.sex} />
              <Info label="年龄区间" value={selectedCase?.age_range} />
              <Info label="生存状态" value={selectedCase?.vital_status} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {genes.map((gene) => (
                <button
                  key={gene}
                  className={`rounded-full border px-3 py-1.5 text-sm font-semibold transition ${selectedGene === gene ? 'border-violet-500 bg-violet-100 text-violet-800' : 'border-gray-200 bg-white text-gray-700 hover:border-violet-300 hover:bg-violet-50'}`}
                  onClick={() => void selectGene(gene)}
                >
                  {gene} 结构
                </button>
              ))}
              {selectedCase && genes.length === 0 && <span className="text-sm text-gray-500">该病例尚无已导入基因变异。</span>}
            </div>
          </div>

          {view === 'cell' ? (
            <PTCCell3D selectedCase={selectedCase} onSelectGene={(gene) => void selectGene(gene)} />
          ) : (
            <PTCProtein3D structure={protein} variants={selectedGeneVariants} loading={proteinLoading} />
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border bg-white p-5 shadow-sm">
              <h3 className="font-bold">病例变异明细</h3>
              <div className="mt-3 max-h-80 overflow-auto">
                {(selectedCase?.variants || []).map((variant) => (
                  <button key={variant.variant_id} className="flex w-full items-center justify-between gap-3 border-b py-2 text-left text-sm hover:bg-gray-50" onClick={() => void selectGene(variant.gene)}>
                    <span><strong>{variant.gene}</strong> · {variant.protein_change || variant.variant_id}</span>
                    <span className="text-xs text-gray-500">{variant.classification || '未分类'}</span>
                  </button>
                ))}
                {!selectedCase?.variants.length && <div className="py-6 text-sm text-gray-500">尚无变异资料。</div>}
              </div>
            </section>
            <section className="rounded-xl border bg-amber-50 p-5 shadow-sm">
              <h3 className="font-bold text-amber-900">结构解释边界</h3>
              <p className="mt-2 text-sm leading-6 text-amber-900/80">
                TCGA 提供的是去识别化病例、病理与分子变异，不包含一颗患者癌细胞的完整显微／原子结构。因此细胞层是多尺度科学示意；蛋白层则使用真实实验 PDB 或 AlphaFold 预测坐标。两者用于研究探索，不能直接作为诊断或用药依据。
              </p>
            </section>
          </div>
        </section>
      </div>
    </main>
  )
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="font-semibold text-gray-900">{value || '—'}</div></div>
}
