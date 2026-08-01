import { useEffect, useMemo, useState } from 'react'

import { createPTCSnapshot, verifyPTCSnapshot, type PTCSnapshot, type PTCSnapshotVerification } from '../api/ptcSnapshots'
import { getLatestPTCCases, type PTCLatestCase } from '../api/ptcVisualization'

export default function PTCSnapshotPage() {
  const [cases, setCases] = useState<PTCLatestCase[]>([])
  const [caseId, setCaseId] = useState('')
  const [gene, setGene] = useState('')
  const [snapshot, setSnapshot] = useState<PTCSnapshot | null>(null)
  const [verification, setVerification] = useState<PTCSnapshotVerification | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getLatestPTCCases(100).then((result) => {
      setCases(result.cases)
      setCaseId(result.cases[0]?.case_id || '')
    }).catch((reason) => setError(reason instanceof Error ? reason.message : '无法载入病例'))
  }, [])

  const selected = useMemo(() => cases.find((item) => item.case_id === caseId) || null, [cases, caseId])
  const genes = useMemo(
    () => Array.from(new Set((selected?.variants || []).map((item) => item.gene.toUpperCase()))).sort(),
    [selected],
  )

  async function generate() {
    if (!caseId) return
    setLoading(true)
    setError(null)
    setVerification(null)
    try {
      const result = await createPTCSnapshot(caseId, gene || undefined)
      setSnapshot(result)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法生成快照')
    } finally {
      setLoading(false)
    }
  }

  function download() {
    if (!snapshot) return
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${snapshot.content.case.case_id}-${snapshot.content.selected_gene || 'all'}-ptc-snapshot.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function verifyFile(file: File | undefined) {
    if (!file) return
    setError(null)
    try {
      const document = JSON.parse(await file.text())
      setVerification(await verifyPTCSnapshot(document))
    } catch (reason) {
      setVerification(null)
      setError(reason instanceof Error ? reason.message : '快照文件无效')
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-cyan-700">PTC Reproducible Research Snapshot</p>
        <h1 className="text-3xl font-bold">可重现研究快照中心</h1>
        <p className="mt-2 max-w-4xl text-gray-600">将病例、变异、Outcome、药物、Evidence、临床试验与导入批次封装为 canonical JSON，并以 SHA-256 检查内容是否被修改。</p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <section className="grid gap-4 rounded-xl border bg-white p-5 shadow-sm md:grid-cols-3">
        <label className="text-sm font-medium">研究病例
          <select className="mt-1 w-full rounded border px-3 py-2" value={caseId} onChange={(event) => { setCaseId(event.target.value); setGene(''); setSnapshot(null) }}>
            {cases.map((item) => <option key={item.case_id} value={item.case_id}>{item.case_id}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">基因范围
          <select className="mt-1 w-full rounded border px-3 py-2" value={gene} onChange={(event) => setGene(event.target.value)}>
            <option value="">全部基因</option>
            {genes.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <div className="flex items-end"><button className="w-full rounded bg-cyan-700 px-4 py-2.5 font-semibold text-white disabled:opacity-50" disabled={!caseId || loading} onClick={() => void generate()}>{loading ? '生成中…' : '生成研究快照'}</button></div>
      </section>

      {snapshot && <section className="mt-6 rounded-xl border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><div className="text-sm text-gray-500">{snapshot.schema}</div><h2 className="text-xl font-bold">{snapshot.content.case.case_id} · {snapshot.content.selected_gene || '全部基因'}</h2></div>
          <button className="rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white" onClick={download}>下载 JSON</button>
        </div>
        <div className="mt-4 break-all rounded bg-slate-950 p-4 font-mono text-sm text-cyan-300"><div>SHA-256</div><strong>{snapshot.checksum_sha256}</strong></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(snapshot.content.counts).map(([name, value]) => <div key={name} className="rounded border p-3"><div className="text-xs text-gray-500">{name}</div><div className="text-2xl font-bold">{value}</div></div>)}
        </div>
        <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{snapshot.disclaimer}</div>
      </section>}

      <section className="mt-6 rounded-xl border bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">验证已下载快照</h2>
        <p className="mt-1 text-sm text-gray-600">重新上传 JSON，服务器会重算 canonical content SHA-256。</p>
        <input className="mt-4 block w-full text-sm" type="file" accept="application/json,.json" onChange={(event) => void verifyFile(event.target.files?.[0])} />
        {verification && <div className={`mt-4 rounded border p-4 ${verification.valid ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'}`}>
          <strong>{verification.valid ? '完整性验证通过' : '完整性验证失败'}</strong>
          <div className="mt-1 text-sm">Case: {verification.case_id || '—'}</div>
          <div className="mt-1 break-all font-mono text-xs">Actual: {verification.actual || '—'}</div>
          {verification.reason && <div className="mt-2 text-sm">{verification.reason}</div>}
        </div>}
      </section>
    </main>
  )
}
