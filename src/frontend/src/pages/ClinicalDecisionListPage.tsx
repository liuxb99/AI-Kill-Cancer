import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchClinicalDecisionsByPatientId, type ClinicalDecisionResponse, type ClinicalDecisionListResponse } from '../api/clinical_decision'

function confidenceBadge(confidence: string): string {
  switch (confidence?.toLowerCase()) {
    case 'high':
    case 'very high':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'medium':
    case 'moderate':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'low':
    case 'very low':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

export default function ClinicalDecisionListPage() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ClinicalDecisionListResponse | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const id = patientId.trim()
    if (!id) { setError('請輸入患者 ID'); return }
    setLoading(true); setError(null); setResult(null)
    try {
      const data = await fetchClinicalDecisionsByPatientId(id)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '查詢臨床決策失敗')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-primary-600 text-xl">&larr;</button>
          <h1 className="text-xl font-bold text-primary-700">臨床決策列表</h1>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">患者 ID</label>
          <div className="flex gap-3">
            <input type="text" value={patientId} onChange={e => setPatientId(e.target.value)} placeholder="請輸入患者 ID 進行查詢" className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent" />
            <button type="submit" disabled={loading} className="bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white rounded-lg px-6 py-2 text-sm font-medium transition">{loading ? '查詢中…' : '查詢'}</button>
          </div>
        </form>
        {loading && <div className="flex flex-col items-center justify-center py-12"><svg className="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 0 00-4 4H4z"/></svg></div>}
        {error && !loading && <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700"><span className="font-medium">錯誤：</span>{error}</div>}
        {!loading && !error && result && result.decisions.length === 0 && <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center"><p className="text-gray-400 text-lg">查無決策記錄</p><p className="text-gray-400 text-sm mt-1">請確認患者 ID 是否正確</p></div>}
        {!loading && !error && result && result.decisions.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-800">查詢結果</h2>
              <span className="text-xs text-gray-400">共 {result.total ?? result.decisions.length} 筆</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"><th className="px-5 py-3">決策類型</th><th className="px-5 py-3">信心等級</th><th className="px-5 py-3">患者 ID</th><th className="px-5 py-3">建立時間</th><th className="px-5 py-3">操作</th></tr></thead>
                <tbody className="divide-y divide-gray-100">
                  {result.decisions.map((d: ClinicalDecisionResponse) => (
                    <tr key={d.decision_id} className="hover:bg-gray-50 transition cursor-pointer" onClick={() => navigate(`/clinical-decision/${d.decision_id}`)}>
                      <td className="px-5 py-4 font-medium text-gray-800">{d.decision_type || '—'}</td>
                      <td className="px-5 py-4"><span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium border ${confidenceBadge(d.confidence)}`}>{d.confidence || '—'}</span></td>
                      <td className="px-5 py-4 font-mono text-xs text-gray-500">{d.patient_id?.length > 16 ? `${d.patient_id.slice(0, 16)}…` : d.patient_id || '—'}</td>
                      <td className="px-5 py-4 text-gray-500">{d.created_at ? formatDateTime(d.created_at) : '—'}</td>
                      <td className="px-5 py-4"><button onClick={e => { e.stopPropagation(); navigate(`/clinical-decision/${d.decision_id}`) }} className="text-primary-600 hover:text-primary-800 text-xs font-medium">查看詳情 &rarr;</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
