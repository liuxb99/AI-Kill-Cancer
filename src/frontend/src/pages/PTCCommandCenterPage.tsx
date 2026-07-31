import { useEffect, useMemo, useState } from 'react'

import {
  getPTCCompleteGraph,
  getPTCOutcomesByGene,
  getPTCSourceStatus,
  syncPTCCompletePipeline,
  type PTCCompleteGraph,
  type PTCOutcomeByGene,
  type PTCSourceStatus,
  type PTCSyncResult,
} from '../api/ptcCompletion'

const DEFAULT_DRUGS = [
  'selpercatinib', 'pralsetinib', 'larotrectinib', 'repotrectinib',
  'dabrafenib', 'trametinib', 'lenvatinib', 'sorafenib', 'cabozantinib',
]

export default function PTCCommandCenterPage() {
  const [status, setStatus] = useState<PTCSourceStatus | null>(null)
  const [outcomes, setOutcomes] = useState<PTCOutcomeByGene[]>([])
  const [graph, setGraph] = useState<PTCCompleteGraph | null>(null)
  const [syncResult, setSyncResult] = useState<PTCSyncResult | null>(null)
  const [gdcSize, setGdcSize] = useState(100)
  const [trialSize, setTrialSize] = useState(100)
  const [pubmedSize, setPubmedSize] = useState(100)
  const [drugText, setDrugText] = useState(DEFAULT_DRUGS.join(', '))
  const [includeCivic, setIncludeCivic] = useState(false)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const [sourceStatus, outcomeRows, graphSnapshot] = await Promise.all([
        getPTCSourceStatus(),
        getPTCOutcomesByGene(),
        getPTCCompleteGraph(500),
      ])
      setStatus(sourceStatus)
      setOutcomes(outcomeRows)
      setGraph(graphSnapshot)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入 PTC 總控台')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  async function runFullSync() {
    setSyncing(true)
    setError(null)
    try {
      const result = await syncPTCCompletePipeline({
        gdc_size: gdcSize,
        trial_size: trialSize,
        pubmed_size: pubmedSize,
        drug_names: drugText.split(',').map((item) => item.trim()).filter(Boolean),
        include_civic: includeCivic,
      })
      setSyncResult(result)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '完整資料同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const graphTypes = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const node of graph?.nodes || []) counts[node.type] = (counts[node.type] || 0) + 1
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [graph])

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <section className="mb-6">
        <p className="text-sm font-semibold text-primary-600">PTC Complete Product Skeleton</p>
        <h1 className="text-3xl font-bold">甲狀腺乳突癌資料與知識總控台</h1>
        <p className="mt-2 text-gray-600">
          一次串聯 TCGA-THCA、ClinicalTrials.gov、openFDA、PubMed、CIViC 與科學中藥研究資料，
          並產生完整病例—變異—基因—藥物—證據—試驗—中藥圖譜。僅供研究與決策支援。
        </p>
      </section>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Metric label="病例" value={status?.cases} />
        <Metric label="變異" value={status?.variants} />
        <Metric label="藥物" value={status?.therapies} />
        <Metric label="證據" value={status?.evidence} />
        <Metric label="試驗" value={status?.clinical_trials} />
        <Metric label="中藥" value={status?.herbs} />
        <Metric label="成分" value={status?.compounds} />
        <Metric label="交互作用" value={status?.interactions} />
        <Metric label="圖節點" value={graph?.node_count} />
        <Metric label="圖關係" value={graph?.edge_count} />
      </section>

      <section className="mt-6 rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">一鍵完成全部公開資料同步</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <NumberField label="GDC 病例數" value={gdcSize} setValue={setGdcSize} />
          <NumberField label="臨床試驗數" value={trialSize} setValue={setTrialSize} />
          <NumberField label="PubMed 文獻數" value={pubmedSize} setValue={setPubmedSize} />
        </div>
        <label className="mt-4 block text-sm font-medium">
          PTC 相關藥物
          <textarea className="mt-1 min-h-24 w-full rounded border px-3 py-2" value={drugText} onChange={(e) => setDrugText(e.target.value)} />
        </label>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input type="checkbox" checked={includeCivic} onChange={(e) => setIncludeCivic(e.target.checked)} />
          同步 CIViC（需要伺服器 CIVIC_API_KEY）
        </label>
        <div className="mt-4 flex gap-3">
          <button className="rounded bg-primary-600 px-5 py-2 text-white disabled:opacity-50" disabled={syncing} onClick={() => void runFullSync()}>
            {syncing ? '完整同步中…' : '執行全部資料鏈'}
          </button>
          <button className="rounded border px-5 py-2" disabled={loading} onClick={() => void refresh()}>重新整理</button>
        </div>
      </section>

      {syncResult && (
        <section className="mt-6 rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-bold">同步結果：{syncResult.status}</h2>
          <p className="mt-1 text-sm text-gray-500">{syncResult.duration_seconds} 秒</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(syncResult.stages).map(([name, stage]) => (
              <div key={name} className="rounded border p-3 text-sm">
                <div className="font-semibold">{name}</div>
                <div className={stage.status === 'success' ? 'text-emerald-700' : stage.status === 'failed' ? 'text-red-700' : 'text-gray-500'}>{stage.status}</div>
                {stage.error && <div className="mt-1 break-words text-xs text-red-600">{stage.error}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-6 grid gap-6 xl:grid-cols-3">
        <Panel title="資料來源">
          {Object.entries(status?.knowledge_sources || {}).map(([source, count]) => (
            <div key={source} className="flex justify-between border-b py-2 text-sm"><span>{source}</span><strong>{count}</strong></div>
          ))}
          {!Object.keys(status?.knowledge_sources || {}).length && <Empty />}
        </Panel>
        <Panel title="圖譜節點類型">
          {graphTypes.map(([kind, count]) => (
            <div key={kind} className="flex justify-between border-b py-2 text-sm"><span>{kind}</span><strong>{count}</strong></div>
          ))}
          {!graphTypes.length && <Empty />}
        </Panel>
        <Panel title="基因與研究 Outcome">
          {outcomes.slice(0, 15).map((item) => (
            <article key={item.gene} className="border-b py-3 last:border-0">
              <div className="flex justify-between"><strong>{item.gene}</strong><span className="text-sm">{item.case_count} cases</span></div>
              <div className="mt-1 text-xs text-gray-500">{Object.entries(item.vital_status).map(([key, value]) => `${key}: ${value}`).join(' · ') || 'No outcome'}</div>
            </article>
          ))}
          {!outcomes.length && <Empty />}
        </Panel>
      </section>

      <section className="mt-6 rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">完整知識圖譜預覽</h2>
        <p className="mt-1 text-sm text-gray-500">目前顯示前 100 條關係；完整資料由 API 提供給 KnowGraphGo 或圖形前端。</p>
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {(graph?.edges || []).slice(0, 100).map((edge) => (
            <div key={edge.id} className="rounded border px-3 py-2 text-xs">
              <div className="font-semibold text-indigo-700">{edge.relation}</div>
              <div className="mt-1 break-all text-gray-500">{edge.source} → {edge.target}</div>
            </div>
          ))}
          {!graph?.edges.length && <Empty />}
        </div>
      </section>
    </main>
  )
}

function Metric({ label, value }: { label: string; value?: number }) {
  return <div className="rounded-lg border bg-white p-4 shadow-sm"><div className="text-xs text-gray-500">{label}</div><div className="mt-1 text-2xl font-bold">{value ?? 0}</div></div>
}

function NumberField({ label, value, setValue }: { label: string; value: number; setValue: (value: number) => void }) {
  return <label className="text-sm font-medium">{label}<input className="mt-1 w-full rounded border px-3 py-2" type="number" min={1} max={1000} value={value} onChange={(e) => setValue(Number(e.target.value))} /></label>
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-lg border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">{title}</h2><div className="mt-3">{children}</div></section>
}

function Empty() { return <div className="py-6 text-sm text-gray-500">尚無資料。</div> }
