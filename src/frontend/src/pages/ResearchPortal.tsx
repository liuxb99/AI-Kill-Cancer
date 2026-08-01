import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listResearchUploads,
  listSandboxHistory,
  runResearchSandbox,
  submitResearchPaper,
  type ResearchPaperPayload,
  type ResearchUpload,
  type SandboxHistoryItem,
} from '../api/researchPortal'

const TABS = [
  { key: 'submit', label: '論文提交' },
  { key: 'data', label: '資料上傳' },
  { key: 'sandbox', label: '模型沙箱' },
] as const

type TabKey = (typeof TABS)[number]['key']

const EMPTY_PAPER: ResearchPaperPayload = {
  title: '', authors: '', journal: '', year: '', doi: '', abstract: '', keywords: '',
}

export default function ResearchPortal() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabKey>('submit')
  const [paperForm, setPaperForm] = useState<ResearchPaperPayload>(EMPTY_PAPER)
  const [paperStatus, setPaperStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [paperError, setPaperError] = useState<string | null>(null)
  const [sandboxInput, setSandboxInput] = useState('')
  const [sandboxRunning, setSandboxRunning] = useState(false)
  const [sandboxResult, setSandboxResult] = useState('')
  const [sandboxError, setSandboxError] = useState<string | null>(null)
  const [uploads, setUploads] = useState<ResearchUpload[]>([])
  const [sandboxHistory, setSandboxHistory] = useState<SandboxHistoryItem[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void Promise.all([listResearchUploads(), listSandboxHistory()])
      .then(([uploadRows, historyRows]) => {
        if (!cancelled) {
          setUploads(uploadRows)
          setSandboxHistory(historyRows)
        }
      })
      .catch((reason) => {
        if (!cancelled) setLoadError(reason instanceof Error ? reason.message : '無法載入研究入口資料')
      })
    return () => { cancelled = true }
  }, [])

  async function handlePaperSubmit(event: React.FormEvent) {
    event.preventDefault()
    setPaperStatus('submitting')
    setPaperError(null)
    try {
      await submitResearchPaper(paperForm)
      setPaperStatus('success')
    } catch (reason) {
      setPaperStatus('error')
      setPaperError(reason instanceof Error ? reason.message : '論文提交失敗')
    }
  }

  async function handleSandboxRun() {
    setSandboxError(null)
    let payload: unknown
    try {
      payload = JSON.parse(sandboxInput)
    } catch {
      setSandboxError('輸入必須是有效 JSON。')
      return
    }

    setSandboxRunning(true)
    setSandboxResult('')
    try {
      const result = await runResearchSandbox(payload)
      setSandboxResult(JSON.stringify(result, null, 2))
    } catch (reason) {
      setSandboxError(reason instanceof Error ? reason.message : '無法連接 API 服務')
    } finally {
      setSandboxRunning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="text-sm text-gray-500 transition hover:text-primary-600">&larr; 回儀表板</button>
            <h1 className="text-xl font-bold text-primary-700">研究入口</h1>
          </div>
          <nav className="flex gap-6 text-sm font-medium text-gray-600">
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/recommendation')}>藥物推薦</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/knowledge')}>知識庫</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/tools')}>工具</span>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">
        {loadError && <div className="mb-5 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">部分資料載入失敗：{loadError}</div>}

        <div className="mb-8 flex gap-1 rounded-xl border border-gray-200 bg-white p-1 shadow-sm">
          {TABS.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition ${activeTab === tab.key ? 'bg-primary-600 text-white shadow' : 'text-gray-500 hover:text-primary-600'}`}>{tab.label}</button>
          ))}
        </div>

        {activeTab === 'submit' && (
          <section>
            <h2 className="mb-4 text-lg font-semibold text-gray-800">提交研究論文</h2>
            {paperStatus === 'success' ? (
              <div className="rounded-xl border border-emerald-200 bg-white p-8 text-center">
                <p className="mb-2 text-lg font-semibold text-emerald-600">論文已成功提交</p>
                <p className="mb-4 text-sm text-gray-500">系統已收到資料，可開始下一筆提交。</p>
                <button onClick={() => { setPaperForm(EMPTY_PAPER); setPaperStatus('idle') }} className="rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">提交新論文</button>
              </div>
            ) : (
              <form onSubmit={handlePaperSubmit} className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
                {paperStatus === 'error' && <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">提交失敗：{paperError}</div>}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field label="論文標題" className="md:col-span-2"><input required value={paperForm.title} onChange={(event) => setPaperForm({ ...paperForm, title: event.target.value })} className="input" /></Field>
                  <Field label="作者"><input required value={paperForm.authors} onChange={(event) => setPaperForm({ ...paperForm, authors: event.target.value })} className="input" /></Field>
                  <Field label="期刊"><input value={paperForm.journal} onChange={(event) => setPaperForm({ ...paperForm, journal: event.target.value })} className="input" /></Field>
                  <Field label="發表年份"><input type="number" value={paperForm.year} onChange={(event) => setPaperForm({ ...paperForm, year: event.target.value })} className="input" /></Field>
                  <Field label="DOI"><input value={paperForm.doi} onChange={(event) => setPaperForm({ ...paperForm, doi: event.target.value })} className="input" /></Field>
                  <Field label="關鍵詞（逗號分隔）" className="md:col-span-2"><input value={paperForm.keywords} onChange={(event) => setPaperForm({ ...paperForm, keywords: event.target.value })} className="input" /></Field>
                  <Field label="摘要" className="md:col-span-2"><textarea required rows={5} value={paperForm.abstract} onChange={(event) => setPaperForm({ ...paperForm, abstract: event.target.value })} className="input" /></Field>
                </div>
                <button type="submit" disabled={paperStatus === 'submitting'} className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white disabled:opacity-50">{paperStatus === 'submitting' ? '提交中…' : '提交論文'}</button>
              </form>
            )}
          </section>
        )}

        {activeTab === 'data' && (
          <section>
            <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold text-gray-800">已上傳資料</h2><label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white">上傳新檔案<input type="file" className="hidden" /></label></div>
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
              <table className="w-full text-sm"><thead className="bg-gray-50 text-gray-500"><tr><th className="px-4 py-3 text-left">檔案名稱</th><th className="px-4 py-3 text-left">類型</th><th className="px-4 py-3 text-left">大小</th><th className="px-4 py-3 text-left">上傳時間</th><th className="px-4 py-3 text-left">狀態</th></tr></thead>
                <tbody className="divide-y divide-gray-100">{uploads.slice(0, 100).map((row, index) => <tr key={`${row.fileName}-${index}`}><td className="px-4 py-3 font-medium">{row.fileName}</td><td className="px-4 py-3 text-gray-500">{row.fileType}</td><td className="px-4 py-3 text-gray-500">{row.fileSize}</td><td className="px-4 py-3 text-gray-500">{row.uploadedAt}</td><td className="px-4 py-3">{row.status}</td></tr>)}</tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === 'sandbox' && (
          <section className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-800">模型測試沙箱</h2>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="rounded-xl border border-gray-200 bg-white p-5"><label className="mb-2 block text-sm font-medium">輸入 JSON</label><textarea aria-label="沙箱 JSON 輸入" rows={8} value={sandboxInput} onChange={(event) => setSandboxInput(event.target.value)} className="input font-mono" placeholder='{"biomarkers":{"BRAF":"p.V600E"}}' /><button onClick={() => void handleSandboxRun()} disabled={sandboxRunning || !sandboxInput} className="mt-3 rounded-lg bg-primary-600 px-5 py-2 text-sm font-medium text-white disabled:opacity-50">{sandboxRunning ? '執行中…' : '執行推論'}</button>{sandboxError && <p className="mt-3 text-sm text-red-600">{sandboxError}</p>}</div>
              <div className="rounded-xl border border-gray-200 bg-white p-5"><label className="mb-2 block text-sm font-medium">推論結果</label><pre className="min-h-[200px] whitespace-pre-wrap rounded-lg bg-gray-900 p-4 text-sm text-gray-100">{sandboxRunning ? '處理中…' : sandboxResult || '等待輸入…'}</pre></div>
            </div>
            <div><h3 className="mb-3 text-sm font-semibold text-gray-700">最近沙箱紀錄</h3><div className="space-y-2">{sandboxHistory.slice(0, 100).map((row, index) => <div key={`${row.model}-${index}`} className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 text-sm"><div><strong className="text-primary-700">{row.model}</strong><p className="mt-0.5 text-xs text-gray-500">{row.input}</p></div><div className="text-right"><p>{row.output}</p><p className="text-xs text-gray-400">{row.latency}</p></div></div>)}</div></div>
          </section>
        )}
      </main>
    </div>
  )
}

function Field({ label, className = '', children }: { label: string; className?: string; children: ReactNode }) {
  return <label className={`block text-sm font-medium text-gray-700 ${className}`}>{label}<div className="mt-1">{children}</div></label>
}
