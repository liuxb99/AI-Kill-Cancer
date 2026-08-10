import { useEffect, useMemo, useState } from 'react'

import {
  getPTCGraphPath,
  listPTCCases,
  type PTCGraphPath,
  type PTCResearchCase,
} from '../api/ptcResearch'
import DemoContextBanner, { useDemoContext } from '../components/DemoContextBanner'

export default function PTCResearchPage() {
  const { synthetic, context: demoContext, loading: demoLoading, error: demoError } = useDemoContext()
  const [cases, setCases] = useState<PTCResearchCase[]>([])
  const [selected, setSelected] = useState<PTCResearchCase | null>(null)
  const [graph, setGraph] = useState<PTCGraphPath | null>(null)
  const [gene, setGene] = useState('')
  const [loading, setLoading] = useState(!synthetic)
  const [error, setError] = useState<string | null>(null)

  async function loadCases(filterGene?: string) {
    if (synthetic) return
    setLoading(true)
    setError(null)
    try {
      const data = await listPTCCases(filterGene || undefined)
      setCases(data)
      const first = data[0] || null
      setSelected(first)
      if (first) setGraph(await getPTCGraphPath(first.case_id))
      else setGraph(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 研究病例')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!synthetic) void loadCases()
  }, [synthetic])

  async function selectCase(item: PTCResearchCase) {
    setSelected(item)
    setError(null)
    try {
      setGraph(await getPTCGraphPath(item.case_id))
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入圖譜路徑')
    }
  }

  const genes = useMemo(
    () => Array.from(new Set(selected?.variants.map((variant) => variant.gene) || [])).sort(),
    [selected],
  )

  if (synthetic) {
    return (
      <main className="max-w-7xl mx-auto px-4 py-8">
        <section className="mb-6">
          <p className="text-sm font-semibold text-primary-600">Papillary Thyroid Carcinoma</p>
          <h1 className="text-3xl font-bold text-gray-900">PTC 研究工作台</h1>
          <p className="mt-2 text-gray-600">以 bundled synthetic case 展示 Case → Variant → Evidence → Drug / Publication / Trial 的研究流程。</p>
        </section>
        {demoError && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{demoError}</div>}
        {demoLoading ? <div className="rounded border bg-white p-8 text-center text-gray-500">載入 Demo Case…</div> : demoContext ? (
          <>
            <DemoContextBanner context={demoContext} label="PTC Research Synthetic Demo" />
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-lg border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold">研究病例摘要</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
                  <Info label="Demo Case" value={demoContext.case_key} />
                  <Info label="Cancer Type" value={demoContext.cancer_type} />
                  <Info label="Stage" value={demoContext.stage} />
                  <Info label="Radioiodine" value={demoContext.radioiodine_status} />
                </div>
              </section>
              <section className="rounded-lg border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold">Variant → Evidence</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
                  <Info label="Gene" value={demoContext.variant.gene} />
                  <Info label="Protein" value={demoContext.variant.hgvs_p} />
                  <Info label="Variant Type" value={demoContext.variant.variant_type} />
                  <Info label="Driver" value={demoContext.variant.driver_status} />
                  <Info label="Evidence Level" value={demoContext.evidence.level} />
                  <Info label="Direction" value={demoContext.evidence.direction} />
                </div>
                <p className="mt-4 text-sm text-gray-600">{demoContext.evidence.summary || 'Synthetic evidence summary unavailable.'}</p>
              </section>
              <section className="rounded-lg border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold">研究關聯</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <Info label="Drug" value={demoContext.drug.name} />
                  <Info label="Mechanism" value={demoContext.drug.mechanism} />
                  <Info label="Publication" value={demoContext.publication.title} />
                  <Info label="Journal" value={demoContext.publication.journal} />
                </div>
              </section>
              <section className="rounded-lg border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold">Clinical Trial Link</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <Info label="Trial" value={demoContext.clinical_trial.id} />
                  <Info label="Title" value={demoContext.clinical_trial.title} />
                  <Info label="Status" value={demoContext.clinical_trial.status} />
                </div>
              </section>
            </div>
          </>
        ) : <div className="rounded border bg-white p-8 text-gray-500">找不到指定 Demo Case。</div>}
      </main>
    )
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">Papillary Thyroid Carcinoma</p>
        <h1 className="text-3xl font-bold text-gray-900">PTC 真實研究病例與基因圖譜</h1>
        <p className="mt-2 text-gray-600">顯示已匯入研究資料庫的公開研究資料。這些是去識別化研究病例，不是臨床患者資料。</p>
      </section>
      <section className="mb-6 flex gap-3">
        <input aria-label="基因篩選" className="w-64 rounded border border-gray-300 px-3 py-2" placeholder="輸入基因，例如 BRAF" value={gene} onChange={(event) => setGene(event.target.value.toUpperCase())} />
        <button className="rounded bg-primary-600 px-4 py-2 text-white hover:bg-primary-700" onClick={() => void loadCases(gene.trim())}>篩選病例</button>
        <button className="rounded border border-gray-300 px-4 py-2 text-gray-700" onClick={() => { setGene(''); void loadCases() }}>清除</button>
      </section>
      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}
      {loading ? <div className="rounded border bg-white p-8 text-center text-gray-500">載入中…</div> : (
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <aside className="rounded-lg border bg-white shadow-sm"><div className="border-b px-4 py-3 font-semibold">研究病例（{cases.length}）</div><div className="max-h-[680px] overflow-auto">
            {cases.map((item) => <button key={`${item.source_dataset}:${item.case_id}`} className={`block w-full border-b px-4 py-3 text-left hover:bg-gray-50 ${selected?.case_id === item.case_id ? 'bg-primary-50' : ''}`} onClick={() => void selectCase(item)}><div className="font-medium text-gray-900">{item.case_id}</div><div className="mt-1 text-xs text-gray-500">{item.pathologic_stage || 'Stage 未提供'} · {item.variants.length} variants</div></button>)}
            {cases.length === 0 && <div className="p-6 text-sm text-gray-500">尚未匯入 PTC 病例。</div>}
          </div></aside>
          <section className="space-y-6">{selected ? <>
            <div className="rounded-lg border bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-xl font-bold">{selected.case_id}</h2><p className="text-sm text-gray-500">{selected.source_dataset}</p></div><div className="rounded bg-emerald-50 px-3 py-1 text-sm text-emerald-700">{selected.vital_status || 'Outcome 未提供'}</div></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm"><Info label="病理分期" value={selected.pathologic_stage} /><Info label="TNM" value={[selected.t_status, selected.n_status, selected.m_status].filter(Boolean).join(' / ')} /><Info label="性別" value={selected.sex} /><Info label="年齡區間" value={selected.age_range} /></div></div>
            <div className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">基因與變異</h2><div className="mt-3 flex flex-wrap gap-2">{genes.map((item) => <span key={item} className="rounded-full bg-indigo-50 px-3 py-1 text-sm text-indigo-700">{item}</span>)}</div><div className="mt-4 overflow-x-auto"><table className="min-w-full text-sm"><thead className="bg-gray-50 text-left text-gray-600"><tr><th className="p-2">Gene</th><th className="p-2">Protein</th><th className="p-2">Location</th><th className="p-2">Classification</th></tr></thead><tbody>{selected.variants.map((variant) => <tr key={variant.variant_id} className="border-t"><td className="p-2 font-semibold">{variant.gene}</td><td className="p-2">{variant.protein_change || '—'}</td><td className="p-2">{variant.chromosome && variant.position ? `${variant.chromosome}:${variant.position}` : '—'}</td><td className="p-2">{variant.classification || '—'}</td></tr>)}</tbody></table></div></div>
            <div className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">最小知識圖譜路徑</h2><p className="mt-1 text-sm text-gray-500">Case → Variant → Gene，並連到 Papillary Thyroid Carcinoma。</p><div className="mt-4 grid gap-4 md:grid-cols-2"><div><h3 className="mb-2 text-sm font-semibold text-gray-600">Nodes</h3><div className="space-y-2">{graph?.nodes.map((node) => <div key={node.id} className="rounded border px-3 py-2 text-sm"><span className="font-semibold">{node.label}</span><span className="ml-2 text-xs text-gray-500">{node.type}</span></div>)}</div></div><div><h3 className="mb-2 text-sm font-semibold text-gray-600">Relations</h3><div className="space-y-2">{graph?.edges.map((edge) => <div key={edge.id} className="rounded border px-3 py-2 text-sm text-gray-700">{edge.relation}</div>)}</div></div></div></div>
          </> : <div className="rounded border bg-white p-8 text-gray-500">請先匯入或選擇病例。</div>}</section>
        </div>
      )}
    </main>
  )
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="font-medium text-gray-900">{value || '—'}</div></div>
}
