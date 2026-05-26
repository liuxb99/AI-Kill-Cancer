import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || ''

const TABS = [
  { key: 'submit', label: '論文提交' },
  { key: 'data', label: '數據上傳' },
  { key: 'sandbox', label: '模型沙箱' },
] as const

type TabKey = (typeof TABS)[number]['key']

interface PaperForm {
  title: string
  authors: string
  journal: string
  year: string
  doi: string
  abstract: string
  keywords: string
}

interface DataUpload {
  fileName: string
  fileType: string
  fileSize: string
  uploadedAt: string
  status: 'success' | 'processing' | 'error'
}

interface SandboxResult {
  model: string
  input: string
  output: string
  latency: string
}

export default function ResearchPortal() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabKey>('submit')
  const [paperForm, setPaperForm] = useState<PaperForm>({ title: '', authors: '', journal: '', year: '', doi: '', abstract: '', keywords: '' })
  const [submitted, setSubmitted] = useState(false)
  const [sandboxInput, setSandboxInput] = useState('')
  const [sandboxRunning, setSandboxRunning] = useState(false)
  const [sandboxResult, setSandboxResult] = useState('')
  const [uploads, setUploads] = useState<DataUpload[]>([])
  const [sandboxHistory, setSandboxHistory] = useState<SandboxResult[]>([])

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/health`)
      .then(r => r.json()).catch(() => {})
    fetch(`${API_BASE}/api/v1/research/uploads`)
      .then(r => r.json()).then(d => setUploads(d)).catch(() => {})
    fetch(`${API_BASE}/api/v1/research/sandbox-history`)
      .then(r => r.json()).then(d => setSandboxHistory(d)).catch(() => {})
  }, [])

  const handlePaperSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await fetch(`${API_BASE}/api/v1/research/papers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(paperForm),
      })
      if (res.ok) setSubmitted(true)
    } catch {
      setSubmitted(true)
    }
  }

  const handleSandboxRun = async () => {
    setSandboxRunning(true)
    setSandboxResult('')
    try {
      const res = await fetch(`${API_BASE}/api/v1/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: sandboxInput,
      })
      const data = await res.json()
      setSandboxResult(JSON.stringify(data, null, 2))
    } catch {
      setSandboxResult('{"error": "無法連接到 API 服務"}')
    }
    setSandboxRunning(false)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/dashboard')} className="text-sm text-gray-500 hover:text-primary-600 transition">
              &larr; 回儀表板
            </button>
            <h1 className="text-xl font-bold text-primary-700">研究入口</h1>
          </div>
          <nav className="flex gap-6 text-sm font-medium text-gray-600">
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/knowledge')}>知識庫</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/tools')}>工具</span>
            <span className="cursor-pointer hover:text-primary-600" onClick={() => navigate('/research')}>論文</span>
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex gap-1 bg-white rounded-xl shadow-sm border border-gray-200 p-1 mb-8">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition ${
                activeTab === tab.key
                  ? 'bg-primary-600 text-white shadow'
                  : 'text-gray-500 hover:text-primary-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'submit' && (
          <section>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">提交研究論文</h2>
            {submitted ? (
              <div className="bg-white rounded-xl border border-accent-200 p-8 text-center">
                <p className="text-accent-600 text-lg font-semibold mb-2">論文已成功提交</p>
                <p className="text-gray-500 text-sm mb-4">我們的團隊將審核您的提交，審核完成後會通過郵件通知。</p>
                <button onClick={() => { setSubmitted(false); setPaperForm({ title: '', authors: '', journal: '', year: '', doi: '', abstract: '', keywords: '' }) }} className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700">
                  提交新論文
                </button>
              </div>
            ) : (
              <form onSubmit={handlePaperSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">論文標題</label>
                    <input value={paperForm.title} onChange={(e) => setPaperForm({ ...paperForm, title: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="Enter paper title" required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">作者</label>
                    <input value={paperForm.authors} onChange={(e) => setPaperForm({ ...paperForm, authors: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="Chen X., Wang L. et al." required />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">期刊</label>
                    <input value={paperForm.journal} onChange={(e) => setPaperForm({ ...paperForm, journal: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="Nature Medicine" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">發表年份</label>
                    <input value={paperForm.year} onChange={(e) => setPaperForm({ ...paperForm, year: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="2026" type="number" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">DOI</label>
                    <input value={paperForm.doi} onChange={(e) => setPaperForm({ ...paperForm, doi: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="10.xxxx/xxxxx" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">關鍵詞（逗號分隔）</label>
                    <input value={paperForm.keywords} onChange={(e) => setPaperForm({ ...paperForm, keywords: e.target.value })} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="deep learning, breast cancer, early detection" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">摘要</label>
                    <textarea value={paperForm.abstract} onChange={(e) => setPaperForm({ ...paperForm, abstract: e.target.value })} rows={5} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400" placeholder="Paper abstract..." required />
                  </div>
                </div>
                <button type="submit" className="px-6 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition">
                  提交論文
                </button>
              </form>
            )}
          </section>
        )}

        {activeTab === 'data' && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">已上傳數據</h2>
              <label className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 transition cursor-pointer">
                上傳新檔案
                <input type="file" className="hidden" />
              </label>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">檔案名稱</th>
                    <th className="text-left px-4 py-3 font-medium">類型</th>
                    <th className="text-left px-4 py-3 font-medium">大小</th>
                    <th className="text-left px-4 py-3 font-medium">上傳時間</th>
                    <th className="text-left px-4 py-3 font-medium">狀態</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {uploads.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{row.fileName}</td>
                      <td className="px-4 py-3 text-gray-500">{row.fileType}</td>
                      <td className="px-4 py-3 text-gray-500">{row.fileSize}</td>
                      <td className="px-4 py-3 text-gray-500">{row.uploadedAt}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          row.status === 'success' ? 'bg-accent-100 text-accent-700' :
                          row.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {row.status === 'success' ? '已完成' : row.status === 'processing' ? '處理中' : '錯誤'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {activeTab === 'sandbox' && (
          <section className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-800">模型測試沙箱</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">輸入參數</label>
                <textarea
                  value={sandboxInput}
                  onChange={(e) => setSandboxInput(e.target.value)}
                  rows={8}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-400"
                  placeholder='{"biomarkers": {"HER2": 3.2, "ER": 0.8}, "age": 55}'
                />
                <button
                  onClick={handleSandboxRun}
                  disabled={sandboxRunning || !sandboxInput}
                  className="mt-3 px-5 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {sandboxRunning ? '執行中...' : '執行推論'}
                </button>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">推論結果</label>
                <div className="bg-gray-900 text-gray-100 rounded-lg p-4 font-mono text-sm min-h-[200px] whitespace-pre-wrap">
                  {sandboxRunning ? '處理中...' : sandboxResult || '等待輸入...'}
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">最近沙箱執行紀錄</h3>
              <div className="space-y-2">
                {sandboxHistory.map((r, i) => (
                  <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between text-sm">
                    <div>
                      <span className="font-semibold text-primary-700">{r.model}</span>
                      <p className="text-gray-500 text-xs mt-0.5">{r.input}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-gray-800">{r.output}</p>
                      <p className="text-gray-400 text-xs">{r.latency}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
