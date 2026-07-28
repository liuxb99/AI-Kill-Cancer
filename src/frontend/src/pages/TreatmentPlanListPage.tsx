/**
 * TreatmentPlanListPage — Treatment Plan 列表頁面
 *
 * 功能：
 * 1. 輸入 patient_id 查詢 Treatment Plans 列表
 * 2. 顯示 plan_id, version, status, intent, goals（精簡）, review_date
 * 3. 狀態顏色標記
 * 4. 點擊進入 Detail 頁
 * 5. "Create New Plan" 按鈕
 *
 * 路由：請在 App.tsx 中加入 <Route path="/treatment-plans" element={<TreatmentPlanListPage />} />
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listTreatmentPlans,
  type TreatmentPlanListItem,
} from '../api/treatmentPlan'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'draft':
      return 'bg-gray-100 text-gray-700 border-gray-200'
    case 'proposed':
      return 'bg-blue-100 text-blue-700 border-blue-200'
    case 'under_review':
      return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'approved':
      return 'bg-green-100 text-green-700 border-green-200'
    case 'active':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'paused':
      return 'bg-purple-100 text-purple-700 border-purple-200'
    case 'completed':
      return 'bg-teal-100 text-teal-700 border-teal-200'
    case 'cancelled':
      return 'bg-red-100 text-red-700 border-red-200'
    case 'superseded':
      return 'bg-orange-100 text-orange-700 border-orange-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function statusLabel(status: string): string {
  switch (status?.toLowerCase()) {
    case 'draft':
      return '草稿'
    case 'proposed':
      return '已提交'
    case 'under_review':
      return '審核中'
    case 'approved':
      return '已核准'
    case 'active':
      return '執行中'
    case 'paused':
      return '已暫停'
    case 'completed':
      return '已完成'
    case 'cancelled':
      return '已取消'
    case 'superseded':
      return '已取代'
    default:
      return status || '—'
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

// ─── Main Component ──────────────────────────────────────────────────────────

export default function TreatmentPlanListPage() {
  const navigate = useNavigate()
  const [patientId, setPatientId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [plans, setPlans] = useState<TreatmentPlanListItem[] | null>(null)
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
    setPlans(null)
    setSkip(0)
    try {
      const data = await listTreatmentPlans(id, 0, limit)
      setPlans(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '查詢 Treatment Plans 失敗')
    } finally {
      setLoading(false)
    }
  }

  const handlePageChange = async (newSkip: number) => {
    if (newSkip < 0) return
    const id = patientId.trim()
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await listTreatmentPlans(id, newSkip, limit)
      setPlans(data)
      setSkip(newSkip)
    } catch (e) {
      setError(e instanceof Error ? e.message : '切換頁面失敗')
    } finally {
      setLoading(false)
    }
  }

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
          <h1 className="text-xl font-bold text-primary-700">Treatment Plans</h1>
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
            <button
              type="button"
              onClick={() => navigate('/treatment-plans/new')}
              className="bg-green-600 hover:bg-green-700 text-white rounded-lg px-6 py-2 text-sm font-medium transition"
            >
              + Create New Plan
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
        {plans !== null && plans.length === 0 && !loading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
            <p className="text-gray-400 text-lg">無 Treatment Plans</p>
            <p className="text-gray-400 text-sm mt-2">
              請先從腫瘤委員會共識頁面建立新的 Treatment Plan
            </p>
          </div>
        )}

        {/* ── Plans List ─────────────────────────────────────────────────── */}
        {plans !== null && plans.length > 0 && !loading && (
          <>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <th className="px-5 py-3">Plan ID</th>
                      <th className="px-5 py-3">Version</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Intent</th>
                      <th className="px-5 py-3">Current</th>
                      <th className="px-5 py-3">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {plans.map((plan) => (
                      <tr
                        key={`${plan.plan_id}-v${plan.version}`}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => navigate(`/treatment-plans/${plan.plan_id}`)}
                      >
                        <td className="px-5 py-3 font-mono text-xs text-gray-600">
                          {plan.plan_id.slice(0, 12)}…
                        </td>
                        <td className="px-5 py-3 text-gray-700">
                          v{plan.version}
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium border ${statusColor(plan.plan_status)}`}
                          >
                            {statusLabel(plan.plan_status)}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-gray-700">
                          {plan.plan_intent || '—'}
                        </td>
                        <td className="px-5 py-3">
                          {plan.is_current ? (
                            <span className="text-green-600 font-medium">✓ 當前</span>
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-gray-500 text-xs">
                          {formatDateTime(plan.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* ── Pagination ────────────────────────────────────────────── */}
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>
                第 {currentPage} 頁（每頁 {limit} 筆）
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => handlePageChange(skip - limit)}
                  disabled={skip === 0}
                  className="px-3 py-1 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  &larr; 上一頁
                </button>
                <button
                  onClick={() => handlePageChange(skip + limit)}
                  disabled={plans.length < limit}
                  className="px-3 py-1 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  下一頁 &rarr;
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
