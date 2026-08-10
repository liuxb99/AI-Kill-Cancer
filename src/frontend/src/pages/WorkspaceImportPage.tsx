import { useEffect, useMemo, useState } from 'react'

import {
  commitWorkspaceImport,
  getWorkspaceImportHistory,
  getWorkspaceStatus,
  previewWorkspaceImport,
  type ImportCommitResult,
  type ImportHistoryItem,
  type ImportPreview,
  type WorkspaceStatus,
} from '../api/workspace'

export default function WorkspaceImportPage() {
  const [status, setStatus] = useState<WorkspaceStatus | null>(null)
  const [sourceDir, setSourceDir] = useState('')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [history, setHistory] = useState<ImportHistoryItem[]>([])
  const [result, setResult] = useState<ImportCommitResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const writable = Boolean(status?.backend === 'sqlite' && status?.persistent && ['local', 'research'].includes(status.app_mode))

  async function refreshHistory() {
    if (!writable) return
    try {
      const data = await getWorkspaceImportHistory(50)
      setHistory(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : '無法載入匯入歷史')
    }
  }

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const current = await getWorkspaceStatus()
        if (!active) return
        setStatus(current)
        if (current.backend === 'sqlite' && current.persistent && ['local', 'research'].includes(current.app_mode)) {
          const data = await getWorkspaceImportHistory(50)
          if (active) setHistory(data.items)
        }
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : '無法載入 Workspace 狀態')
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => { active = false }
  }, [])

  async function runPreview() {
    if (!sourceDir.trim()) return
    setWorking(true)
    setError(null)
    setResult(null)
    try {
      setPreview(await previewWorkspaceImport(sourceDir.trim()))
    } catch (err) {
      setPreview(null)
      setError(err instanceof Error ? err.message : '預覽失敗')
    } finally {
      setWorking(false)
    }
  }

  async function runImport() {
    if (!preview?.validation.ok) return
    setWorking(true)
    setError(null)
    try {
      const data = await commitWorkspaceImport(sourceDir.trim())
      setResult(data)
      setPreview(await previewWorkspaceImport(sourceDir.trim()))
      await refreshHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : '匯入失敗')
    } finally {
      setWorking(false)
    }
  }

  const duplicateRows = useMemo(() => Object.entries(preview?.duplicates || {}), [preview])

  if (loading) {
    return <main className="max-w-6xl mx-auto px-4 py-8"><div className="rounded border bg-white p-8 text-gray-500">載入 Workspace 狀態…</div></main>
  }

  return (
    <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <section>
        <p className="text-sm font-semibold text-primary-600">Local-First Research Workspace</p>
        <h1 className="text-3xl font-bold text-gray-900">Workspace CSV 匯入</h1>
        <p className="mt-2 text-gray-600">先驗證與預覽，再顯式匯入。既有 deterministic records 只會跳過，不會覆寫。</p>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm" data-testid="workspace-status-card">
        <h2 className="text-lg font-bold">Workspace 狀態</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
          <Info label="App Mode" value={status?.app_mode} />
          <Info label="Backend" value={status?.backend} />
          <Info label="Persistent" value={status?.persistent ? 'yes' : 'no'} />
          <Info label="Database" value={status?.database_path || '—'} />
        </div>
      </section>

      {!writable ? (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5" data-testid="workspace-import-guard">
          <h2 className="font-bold text-amber-900">此環境不可寫入</h2>
          <p className="mt-2 text-sm text-amber-800">CSV Import 只在 local/research + persistent SQLite 啟用。Demo/Vercel runtime 只提供展示，不提供寫入。</p>
        </section>
      ) : (
        <>
          <section className="rounded-lg border bg-white p-5 shadow-sm">
            <label className="block text-sm font-semibold text-gray-700" htmlFor="source-dir">CSV Dataset 目錄</label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <input id="source-dir" aria-label="CSV Dataset 目錄" className="min-w-0 flex-1 rounded border border-gray-300 px-3 py-2" placeholder="D:/research/ptc-dataset" value={sourceDir} onChange={(event) => { setSourceDir(event.target.value); setPreview(null); setResult(null) }} />
              <button className="rounded bg-primary-600 px-5 py-2 font-medium text-white disabled:opacity-50" disabled={working || !sourceDir.trim()} onClick={() => void runPreview()}>{working ? '處理中…' : 'Validate / Preview'}</button>
            </div>
            <p className="mt-2 text-xs text-gray-500">Browser 無法直接選取本機資料夾路徑給後端；目前 UI 採明確路徑輸入，下一版再評估 desktop file picker bridge。</p>
          </section>

          {preview && (
            <section className="rounded-lg border bg-white p-5 shadow-sm" data-testid="import-preview">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div><h2 className="text-lg font-bold">匯入預覽</h2><p className="text-sm text-gray-500">{preview.source_dir}</p></div>
                <span className={`rounded-full px-3 py-1 text-sm ${preview.validation.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>{preview.validation.ok ? 'Validation PASS' : 'Validation FAIL'}</span>
              </div>

              {!preview.validation.ok && <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-red-700">{preview.validation.errors.map((item) => <li key={item}>{item}</li>)}</ul>}

              {duplicateRows.length > 0 && <div className="mt-5 overflow-x-auto"><table className="min-w-full text-sm"><thead className="bg-gray-50 text-left text-gray-600"><tr><th className="p-2">Entity</th><th className="p-2">Total</th><th className="p-2">Existing / Skip</th><th className="p-2">New / Import</th></tr></thead><tbody>{duplicateRows.map(([name, item]) => <tr key={name} className="border-t"><td className="p-2 font-medium">{name}</td><td className="p-2">{item.total}</td><td className="p-2">{item.existing}</td><td className="p-2">{item.new}</td></tr>)}</tbody></table></div>}

              <div className="mt-5 rounded bg-gray-50 p-3 text-sm text-gray-700">Overwrite existing: <strong>NO</strong>. Import 必須經過本頁 Preview，按下按鈕才會送出後端要求的 <code>confirm=IMPORT</code>。</div>
              <button data-testid="confirm-import" className="mt-4 rounded bg-emerald-600 px-5 py-2 font-semibold text-white disabled:opacity-50" disabled={working || !preview.validation.ok} onClick={() => void runImport()}>Explicit Import</button>
            </section>
          )}

          {result && <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-5" data-testid="import-result"><h2 className="font-bold text-emerald-900">匯入完成</h2><p className="mt-2 text-sm text-emerald-800">{result.message}</p><div className="mt-3 text-sm text-emerald-900">History: {result.history_path}</div></section>}

          <section className="rounded-lg border bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-bold">Import History</h2><button className="rounded border px-3 py-1 text-sm" onClick={() => void refreshHistory()}>重新整理</button></div>
            <div className="mt-4 space-y-3" data-testid="import-history">
              {history.map((item, index) => <article key={`${item.timestamp || 'history'}-${index}`} className="rounded border p-3 text-sm"><div className="font-medium">{item.source_dir || 'Unknown source'}</div><div className="mt-1 text-xs text-gray-500">{item.timestamp || '—'}</div><div className="mt-2 text-gray-700">Imported: {Object.entries(item.imported || {}).map(([key, value]) => `${key}=${value}`).join(', ') || '—'}</div></article>)}
              {history.length === 0 && <p className="text-sm text-gray-500">尚無匯入歷史。</p>}
            </div>
          </section>
        </>
      )}

      {error && <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</div>}
    </main>
  )
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return <div><div className="text-xs text-gray-500">{label}</div><div className="break-all font-medium text-gray-900">{value || '—'}</div></div>
}
