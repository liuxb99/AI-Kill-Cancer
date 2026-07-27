/**
 * TumorBoardConsensusPage — 腫瘤委員會共識明細頁面
 *
 * 功能：
 * 1. 從 URL 取得 consensus_id
 * 2. 呼叫 GET /api/v1/tumor-board/consensus/{id} 取得共識資料
 * 3. 顯示 Consensus Status、Score、Final Recommendation、Supporting Rationale、
 *    Dissenting Opinions、Unresolved Questions、Required Follow-up、
 *    Specialist Opinions 表格、Trace Summary
 *
 * 路由：請在 App.tsx 中加入 <Route path="/tumor-board/:id" element={<TumorBoardConsensusPage />} />
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getTumorBoardConsensus,
  getTumorBoardConsensusOpinions,
  getTumorBoardConsensusTrace,
  type TumorBoardConsensus,
  type SpecialistOpinion,
} from '../api/workbench'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'unanimous':
      return 'text-green-600 bg-green-50 border-green-200'
    case 'strong_consensus':
      return 'text-blue-600 bg-blue-50 border-blue-200'
    case 'majority_consensus':
      return 'text-amber-600 bg-amber-50 border-amber-200'
    case 'split_decision':
      return 'text-orange-600 bg-orange-50 border-orange-200'
    case 'insufficient_information':
      return 'text-gray-600 bg-gray-50 border-gray-200'
    case 'deferred':
      return 'text-purple-600 bg-purple-50 border-purple-200'
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200'
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

function confidenceBadge(confidence: number | string): string {
  // Handle numeric confidence (0.0–1.0 scale for specialist opinions)
  if (typeof confidence === 'number') {
    if (confidence >= 0.7) return 'bg-green-100 text-green-800 border-green-200'
    if (confidence >= 0.4) return 'bg-amber-100 text-amber-800 border-amber-200'
    return 'bg-red-100 text-red-800 border-red-200'
  }
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

export default function TumorBoardConsensusPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [consensus, setConsensus] = useState<TumorBoardConsensus | null>(null)
  const [opinions, setOpinions] = useState<SpecialistOpinion[] | null>(null)
  const [traceSummary, setTraceSummary] = useState<string | null>(null)
  const [opinionsLoading, setOpinionsLoading] = useState(false)
  const [traceLoading, setTraceLoading] = useState(false)

  useEffect(() => {
    if (!id) {
      setError('缺少共識 ID')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    getTumorBoardConsensus(id)
      .then((data) => {
        if (!cancelled) {
          setConsensus(data)
          // 如果 consensus 已有 specialist_opinions 且有意見，就不另外請求
          if (!data.specialist_opinions || data.specialist_opinions.length === 0) {
            setOpinionsLoading(true)
            getTumorBoardConsensusOpinions(id)
              .then((opts) => {
                if (!cancelled) setOpinions(opts)
              })
              .catch(() => {
                // 忽略 opinions 子請求錯誤
              })
              .finally(() => {
                if (!cancelled) setOpinionsLoading(false)
              })
          }
          setTraceLoading(true)
          getTumorBoardConsensusTrace(id)
            .then((trace) => {
              if (!cancelled) setTraceSummary(JSON.stringify(trace, null, 2))
            })
            .catch(() => {
              // 忽略 trace 子請求錯誤
            })
            .finally(() => {
              if (!cancelled) setTraceLoading(false)
            })
        }
      })
      .catch((e) => {
        if (!cancelled) {
          const message = e instanceof Error ? e.message : '載入腫瘤委員會共識失敗'
          // 404 處理
          if (message.includes('404') || message.includes('Not Found')) {
            setError('找不到此共識記錄（ID 可能無效）')
          } else {
            setError(message)
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
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
          <h1 className="text-xl font-bold text-primary-700">腫瘤委員會共識</h1>
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
                d="M4 12a8 8 0 018-8v4a4 0 00-4 4H4z"
              />
            </svg>
            <p className="text-sm text-gray-500">正在載入共識資料，請稍候…</p>
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
        {!loading && !error && !consensus && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
            <p className="text-gray-400 text-lg">無共識資料</p>
          </div>
        )}

        {/* ── Consensus Detail ───────────────────────────────────────────── */}
        {consensus && !loading && (
          <>
            {/* Header info bar */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-gray-800">共識詳情</h2>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                {consensus.consensus_id && (
                  <span>ID: {consensus.consensus_id.slice(0, 12)}…</span>
                )}
                {consensus.created_at && (
                  <span>· {formatDateTime(consensus.created_at)}</span>
                )}
                {consensus.updated_at && consensus.updated_at !== consensus.created_at && (
                  <span className="text-gray-300">
                    · 更新: {formatDateTime(consensus.updated_at)}
                  </span>
                )}
              </div>
            </div>

            {/* Status & Score */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  共識狀態（Status）
                </label>
                <span
                  className={`inline-block rounded-full px-3 py-1 text-xs font-medium border ${statusColor(consensus.consensus_status)}`}
                >
                  {statusLabel(consensus.consensus_status)}
                </span>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  共識分數（Consensus Score）
                </label>
                <p className="text-base font-medium text-gray-800">
                  {consensus.consensus_score != null ? consensus.consensus_score : '—'}
                </p>
              </div>
            </div>

            {/* Patient ID & Clinical Decision ID */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {consensus.patient_id && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                    患者 ID
                  </label>
                  <p className="text-sm text-gray-700 font-mono">
                    {consensus.patient_id}
                  </p>
                  <a
                    href={`/clinical-graph?patientId=${consensus.patient_id}`}
                    className="inline-flex items-center gap-1 mt-2 text-xs text-primary-600 hover:text-primary-800"
                  >
                    View in Knowledge Graph &rarr;
                  </a>
                </div>
              )}
              {consensus.clinical_decision_id && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
                    臨床決策 ID
                  </label>
                  <p className="text-sm text-gray-700 font-mono">
                    {consensus.clinical_decision_id}
                  </p>
                </div>
              )}
            </div>

            {/* Final Recommendation */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                最終建議（Final Recommendation）
              </label>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {consensus.final_recommendation || '無建議'}
              </p>
            </div>

            {/* Supporting Rationale */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                支持理由（Supporting Rationale）
              </label>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {consensus.supporting_rationale || '無說明'}
              </p>
            </div>

            {/* Dissenting Opinions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                異議意見（Dissenting Opinions）
              </label>
              {consensus.dissenting_opinions && consensus.dissenting_opinions.length > 0 ? (
                <ul className="space-y-2">
                  {consensus.dissenting_opinions.map((op, i) => (
                    <li
                      key={i}
                      className="bg-orange-50 border border-orange-100 rounded-lg p-3 text-sm text-orange-800"
                    >
                      {op}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">無異議意見</p>
              )}
            </div>

            {/* Unresolved Questions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                未解決問題（Unresolved Questions）
              </label>
              {consensus.unresolved_questions && consensus.unresolved_questions.length > 0 ? (
                <ul className="space-y-1.5">
                  {consensus.unresolved_questions.map((q, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-gray-700"
                    >
                      <span className="text-gray-300 mt-0.5">•</span>
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">無未解決問題</p>
              )}
            </div>

            {/* Required Follow-up */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                需追蹤事項（Required Follow-up）
              </label>
              {consensus.required_follow_up && consensus.required_follow_up.length > 0 ? (
                <ul className="space-y-1.5">
                  {consensus.required_follow_up.map((f, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-sm text-gray-700"
                    >
                      <span className="text-blue-400 mt-0.5">&#9654;</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">無需追蹤事項</p>
              )}
            </div>

            {/* Specialist Opinions Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">
                  專科意見（Specialist Opinions）
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <th className="px-5 py-3">專科</th>
                      <th className="px-5 py-3">立場</th>
                      <th className="px-5 py-3">信心度</th>
                      <th className="px-5 py-3">理由</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(consensus.specialist_opinions && consensus.specialist_opinions.length > 0
                      ? consensus.specialist_opinions
                      : opinions && opinions.length > 0
                        ? opinions
                        : []
                    ).length > 0 ? (
                      (consensus.specialist_opinions && consensus.specialist_opinions.length > 0
                        ? consensus.specialist_opinions
                        : opinions || []
                      ).map((op, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-5 py-3 font-medium text-gray-800">
                            {op.specialty || '—'}
                          </td>
                          <td className="px-5 py-3 text-gray-700">
                            {op.position || '—'}
                          </td>
                          <td className="px-5 py-3">
                            <span
                              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${confidenceBadge(op.confidence)}`}
                            >
                              {op.confidence || '—'}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-gray-600 max-w-md whitespace-pre-wrap">
                            {op.rationale || '—'}
                          </td>
                        </tr>
                      ))
                    ) : opinionsLoading ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-5 py-6 text-center text-sm text-gray-400"
                        >
                          載入中…
                        </td>
                      </tr>
                    ) : (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-5 py-6 text-center text-sm text-gray-400"
                        >
                          無專科意見
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Trace Summary */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                推理軌跡摘要（Trace Summary）
              </label>
              {traceLoading ? (
                <p className="text-sm text-gray-400">載入中…</p>
              ) : traceSummary ? (
                <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
                  {traceSummary}
                </pre>
              ) : consensus.trace_id ? (
                <pre className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
                  {consensus.trace_id}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">無推理軌跡</p>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
