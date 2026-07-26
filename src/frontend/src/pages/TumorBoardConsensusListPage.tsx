/**
 * TumorBoardConsensusListPage — 腫瘤委員會共識列表頁面
 *
 * 功能：
 * 1. 輸入 patient_id 查詢共識列表
 * 2. 顯示 Consensus 列表（status, score, specialties, created_at）
 * 3. 點擊進入明細頁
 * 4. 分頁（skip/limit）
 *
 * 路由：請在 App.tsx 中加入 <Route path="/tumor-board" element={<TumorBoardConsensusListPage />} />
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listTumorBoardConsensus,
  type TumorBoardConsensus,
} from '../api/workbench'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'unanimous':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'strong_consensus':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'majority_consensus':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'split_decision':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'insufficient_information':
      return 'bg-gray-100 text-gray-600 border-gray-200'
    case 'deferred':
      return 'bg-purple-100 text-purple-800 border-purple-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function statusLabel(status: string): string {
  switch (status?.toLowerCase()) {
    case 'unanimous':
      return '一致通過'
    case 'strong_consensus':
      return '強共識'
    case 'majority_consensus':
      return '多數共識'
    case 'split_decision':
      return '意見分歧'
    case 'insufficient_information':
      return '資訊不足'
    case 'deferred':
      return '暫緩'
    default:
      return status || '—'
  }
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function TumorBoardConsensusListPage() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TumorBoardConsensus[] | null>(null)
  const [skip, setSkip] = useState(0)
  const limit = 20

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const id = patientId.trim()
    if (!id) {
      setError('請輸入患者 ID')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    setSkip(0)
    try {
      const data = await listTumorBoardConsensus(id, 0, limit)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '查詢腫瘤委員會共識失敗')
    } finally {
      setLoading(false)
    }
  }

  const handlePageChange = async (newSkip: number) => {
    if (newSkip < 0 || (result && newSkip >= result.length)) return
    const id = patientId.trim()
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await listTumorBoardConsensus(id, newSkip, limit)
      setResult(data)
      setSkip(newSkip)
    } catch (e) {
      setError(e instanceof Error ? e.message : '切換頁面失敗')
    } finally {
      setLoading(false)
    }
  }

  const totalPages = result ? Math.ceil(result.length / limit) : 0
  const currentPage = Math.floor(skip / limit) + 1

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="text-gray-400 hover:text-primary-600 text-xl"
          >
            &larr;
          </button>
          <h1 className="text-xl font-bold text-primary-700">腫瘤委員會共識列表</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        {/* ── Search Form ────────────────────────────────────────────────── */}
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-xl shadow-sm border border-gray-100 p-6"
        >
          <label className="block text-sm font-medium text-gray-700 mb-2">
            患者 ID
          </label>
          <div className="flex gap-3">
            <input
              type="text"
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              placeholder="請輸入患者 ID 進行查詢"
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white rounded-lg px-6 py-2 text-sm font-medium transition"
            >
              {loading ? '查詢中…' : '查詢'}
            </button>
          </div>
        </form>

        {/* ── Loading State ──────────────────────────────────────────────── */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <svg
              className="animate-spin h-8 w-8 text-primary-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 0 00-4 4H4z"
              />
            </svg>
          </div>
        )}

        {/* ── Error State ────────────────────────────────────────────────── */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
            <span className="font-medium">錯誤：</span>
            {error}
          </div>
        )}

        {/* ── Empty State ────────────────────────────────────────────────── */}
        {!loading && !error && result && result.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
            <p className="text-gray-400 text-lg">查無共識記錄</p>
            <p className="text-gray-400 text-sm mt-1">請確認患者 ID 是否正確</p>
          </div>
        )}

        {/* ── Consensus List ─────────────────────────────────────────────── */}
        {!loading && !error && result && result.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-800">查詢結果</h2>
              <span className="text-xs text-gray-400">
                共 {result.length} 筆
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <th className="px-5 py-3">狀態</th>
                    <th className="px-5 py-3">共識分數</th>
                    <th className="px-5 py-3">專科領域</th>
                    <th className="px-5 py-3">建立時間</th>
                    <th className="px-5 py-3">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.map((c: TumorBoardConsensus) => (
                    <tr
                      key={c.consensus_id}
                      className="hover:bg-gray-50 transition cursor-pointer"
                      onClick={() => navigate(`/tumor-board/${c.consensus_id}`)}
                    >
                      <td className="px-5 py-4">
                        <span
                          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium border ${statusColor(c.consensus_status)}`}
                        >
                          {statusLabel(c.consensus_status)}
                        </span>
                      </td>
                      <td className="px-5 py-4 font-medium text-gray-800">
                        {c.consensus_score != null ? c.consensus_score : '—'}
                      </td>
                      <td className="px-5 py-4 text-gray-600">
                        {c.participating_specialties?.length > 0
                          ? c.participating_specialties.join(', ')
                          : '—'}
                      </td>
                      <td className="px-5 py-4 text-gray-500">
                        {c.created_at ? formatDateTime(c.created_at) : '—'}
                      </td>
                      <td className="px-5 py-4">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/tumor-board/${c.consensus_id}`)
                          }}
                          className="text-primary-600 hover:text-primary-800 text-xs font-medium"
                        >
                          查看詳情 &rarr;
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── Pagination ──────────────────────────────────────────────── */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-gray-50">
                <button
                  onClick={() => handlePageChange(skip - limit)}
                  disabled={skip === 0 || loading}
                  className="text-sm text-gray-600 hover:text-primary-600 disabled:text-gray-300 disabled:cursor-not-allowed transition"
                >
                  &larr; 上一頁
                </button>
                <span className="text-xs text-gray-500">
                  第 {currentPage} / {totalPages} 頁
                </span>
                <button
                  onClick={() => handlePageChange(skip + limit)}
                  disabled={(result && skip + limit >= result.length) || loading}
                  className="text-sm text-gray-600 hover:text-primary-600 disabled:text-gray-300 disabled:cursor-not-allowed transition"
                >
                  下一頁 &rarr;
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
