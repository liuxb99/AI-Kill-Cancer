/**
 * ClinicalDecisionPage — 臨床決策頁面
 *
 * 功能：
 * 1. 從 URL 取得 decision_id
 * 2. 呼叫 GET /api/v1/clinical-decision/{id} 取得決策資料
 * 3. 顯示決策類型、理由、信心等級、證據摘要、替代方案、禁忌症
 *
 * 路由：請在 App.tsx 中加入 <Route path="/clinical-decision/:id" element={<ClinicalDecisionPage />} />
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchClinicalDecisionById, type ClinicalDecisionResponse } from '../api/clinical_decision'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function confidenceColor(confidence: string): string {
  switch (confidence?.toLowerCase()) {
    case 'high':
    case 'very high':
      return 'text-green-600 bg-green-50 border-green-200'
    case 'medium':
    case 'moderate':
      return 'text-amber-600 bg-amber-50 border-amber-200'
    case 'low':
    case 'very low':
      return 'text-red-600 bg-red-50 border-red-200'
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200'
  }
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
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

export default function ClinicalDecisionPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [decision, setDecision] = useState<ClinicalDecisionResponse | null>(null)

  useEffect(() => {
    if (!id) {
      setError('缺少決策 ID')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    fetchClinicalDecisionById(id)
      .then((data) => {
        if (!cancelled) setDecision(data)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '載入臨床決策失敗')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [id])

  // ── Render ──────────────────────────────────────────────────────────────────

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
          <h1 className="text-xl font-bold text-primary-700">臨床決策</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        {/* ── Loading State ──────────────────────────────────────────────── */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <svg
              className="animate-spin h-10 w-10 text-primary-500"
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
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
              />
            </svg>
            <p className="text-sm text-gray-500">正在載入臨床決策，請稍候…</p>
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
        {!loading && !error && !decision && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
            <p className="text-gray-400 text-lg">無決策資料</p>
          </div>
        )}

        {/* ── Decision Detail ────────────────────────────────────────────── */}
        {decision && !loading && (
          <>
            {/* Header info bar */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-gray-800">
                決策詳情
              </h2>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                {decision.decision_id && (
                  <span>ID: {decision.decision_id.slice(0, 12)}…</span>
                )}
                {decision.created_at && (
                  <span>· {formatDateTime(decision.created_at)}</span>
                )}
                {decision.trace_id && (
                  <span className="text-gray-300" title={decision.trace_id}>
                    · trace: {decision.trace_id.slice(0, 8)}…
                  </span>
                )}
              </div>
            </div>

            {/* Decision Type & Confidence */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  決策類型
                </label>
                <p className="text-base font-medium text-gray-800">
                  {decision.decision_type || '—'}
                </p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  信心等級
                </label>
                <span
                  className={`inline-block rounded-full px-3 py-1 text-xs font-medium border ${confidenceColor(decision.confidence)}`}
                >
                  {decision.confidence || '—'}
                </span>
              </div>
            </div>

            {/* Reason */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                理由（Reason）
              </label>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {decision.reason || '無說明'}
              </p>
            </div>

            {/* Evidence Summary */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                證據摘要（Evidence Summary）
              </label>
              {decision.evidence_summary ? (
                <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(decision.evidence_summary, null, 2)}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">無證據摘要</p>
              )}
            </div>

            {/* Alternatives */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                替代方案（Alternatives）
              </label>
              {decision.alternatives && decision.alternatives.length > 0 ? (
                <div className="space-y-2">
                  {decision.alternatives.map((alt, i) => (
                    <div
                      key={i}
                      className="bg-gray-50 rounded-lg border border-gray-100 p-3 text-sm"
                    >
                      <pre className="text-gray-700 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(alt, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無替代方案</p>
              )}
            </div>

            {/* Contraindications */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                禁忌症（Contraindications）
              </label>
              {decision.contraindications && decision.contraindications.length > 0 ? (
                <div className="space-y-2">
                  {decision.contraindications.map((ci, i) => (
                    <div
                      key={i}
                      className="bg-red-50 rounded-lg border border-red-100 p-3 text-sm"
                    >
                      <pre className="text-red-700 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(ci, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無禁忌症</p>
              )}
            </div>

            {/* Patient & Recommendation IDs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                  Patient ID
                </label>
                <p className="text-sm text-gray-700 font-mono">
                  {decision.patient_id || '—'}
                </p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                  Recommendation ID
                </label>
                <p className="text-sm text-gray-700 font-mono">
                  {decision.recommendation_id || '—'}
                </p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
