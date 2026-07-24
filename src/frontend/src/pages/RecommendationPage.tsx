/**
 * RecommendationPage — 藥物推薦頁面
 *
 * 功能：
 * 1. 輸入 Patient ID、Variants（每行一個）、Top N
 * 2. 呼叫 POST /api/v1/recommendation 取得推薦結果
 * 3. 顯示 Top Drugs 排名表（可展開查看 Reason）
 * 4. 顯示原始 Response JSON（可摺疊）
 *
 * 路由：請在 App.tsx 中加入 <Route path="/recommendation" element={<RecommendationPage />} />
 */

import { useState, useCallback, Fragment } from 'react'
import { useNavigate } from 'react-router-dom'

// ─── API base ────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL || ''

// ─── Types ───────────────────────────────────────────────────────────────────

interface Explanation {
  category: string
  detail: string
  source: string
  score_impact: number
  trace_id?: string
}

interface DrugItem {
  drug_name: string
  rank: number
  overall_score: number
  evidence_score: number
  sensitivity_score: number
  resistance_score: number
  conflict_score: number
  explanations: Explanation[]
}

interface RecommendationResult {
  recommendation_id: string
  patient_id: string
  recommendations: DrugItem[]
  trace_id: string
  engine_version: string
  created_at: string
}

// ─── API call ────────────────────────────────────────────────────────────────

async function fetchRecommendation(
  patientId: string,
  variants: string[],
  topN: number,
): Promise<RecommendationResult> {
  const res = await fetch(`${API_BASE}/api/v1/recommendation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patient_id: patientId,
      variants,
      top_n: topN,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || err.message || `HTTP ${res.status}`)
  }

  return res.json()
}

// ─── Helper: score color ─────────────────────────────────────────────────────

function scoreColor(value: number): string {
  if (value >= 0.7) return 'text-green-600'
  if (value >= 0.4) return 'text-amber-600'
  return 'text-red-600'
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function RecommendationPage() {
  const navigate = useNavigate()

  // Form state
  const [patientId, setPatientId] = useState('')
  const [variantsText, setVariantsText] = useState('')
  const [topN, setTopN] = useState(5)

  // Fetch state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RecommendationResult | null>(null)

  // UI state
  const [expandedDrugs, setExpandedDrugs] = useState<Set<string>>(new Set())
  const [showRawJson, setShowRawJson] = useState(false)

  const handleSubmit = useCallback(async () => {
    const trimmedPatientId = patientId.trim()
    if (!trimmedPatientId) {
      setError('請輸入 Patient ID')
      return
    }

    const variants = variantsText
      .split('\n')
      .map((v) => v.trim())
      .filter(Boolean)

    if (variants.length === 0) {
      setError('請輸入至少一個 Variant')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setExpandedDrugs(new Set())
    setShowRawJson(false)

    try {
      const data = await fetchRecommendation(trimmedPatientId, variants, topN)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '推薦請求失敗')
    } finally {
      setLoading(false)
    }
  }, [patientId, variantsText, topN])

  const toggleDrug = (drugName: string) => {
    setExpandedDrugs((prev) => {
      const next = new Set(prev)
      if (next.has(drugName)) {
        next.delete(drugName)
      } else {
        next.add(drugName)
      }
      return next
    })
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-primary-600 text-xl"
          >
            &larr;
          </button>
          <h1 className="text-xl font-bold text-primary-700">藥物推薦</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        {/* ── Input Section ────────────────────────────────────────────── */}
        <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">輸入參數</h2>

          <div className="space-y-4">
            {/* Patient ID */}
            <div>
              <label
                htmlFor="patient-id"
                className="block text-sm font-medium text-gray-600 mb-1"
              >
                Patient ID
              </label>
              <input
                id="patient-id"
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="例如：P-10001"
                className="w-full max-w-sm rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           placeholder:text-gray-300"
              />
            </div>

            {/* Variants */}
            <div>
              <label
                htmlFor="variants"
                className="block text-sm font-medium text-gray-600 mb-1"
              >
                Variants（每行一個）
              </label>
              <textarea
                id="variants"
                rows={5}
                value={variantsText}
                onChange={(e) => setVariantsText(e.target.value)}
                placeholder="EGFR L858R&#10;KRAS G12C&#10;BRAF V600E"
                className="w-full max-w-lg rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
                           placeholder:text-gray-300 resize-y"
              />
            </div>

            {/* Top N */}
            <div>
              <label
                htmlFor="top-n"
                className="block text-sm font-medium text-gray-600 mb-1"
              >
                Top N
              </label>
              <select
                id="top-n"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </div>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm
                         font-medium text-white shadow-sm hover:bg-primary-700
                         disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4 text-white"
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
                  生成中…
                </>
              ) : (
                'Generate Recommendation'
              )}
            </button>
          </div>
        </section>

        {/* ── Error State ──────────────────────────────────────────────── */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
            <span className="font-medium">錯誤：</span>
            {error}
          </div>
        )}

        {/* ── Loading State ────────────────────────────────────────────── */}
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
            <p className="text-sm text-gray-500">正在生成推薦，請稍候…</p>
          </div>
        )}

        {/* ── Results Section ──────────────────────────────────────────── */}
        {result && !loading && (
          <>
            {/* Result header */}
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-800">
                推薦結果
              </h2>
              <span className="text-xs text-gray-400">
                {result.recommendation_id
                  ? `ID: ${result.recommendation_id.slice(0, 12)}…`
                  : ''}
                {result.created_at &&
                  ` · ${new Date(result.created_at).toLocaleString('zh-CN')}`}
              </span>
            </div>

            {/* Top Drugs Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <th className="px-4 py-3 w-12">Rank</th>
                    <th className="px-4 py-3">Drug Name</th>
                    <th className="px-4 py-3 text-right">Overall Score</th>
                    <th className="px-4 py-3 text-right">Evidence</th>
                    <th className="px-4 py-3 text-right">Sensitivity</th>
                    <th className="px-4 py-3 text-right">Resistance</th>
                    <th className="px-4 py-3 w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.recommendations.map((drug) => {
                    const isExpanded = expandedDrugs.has(drug.drug_name)
                    return (
                      <Fragment key={drug.drug_name}>
                        <tr
                          className="hover:bg-gray-50 cursor-pointer transition"
                          onClick={() => toggleDrug(drug.drug_name)}
                        >
                          <td className="px-4 py-3 font-medium text-gray-700">
                            {drug.rank}
                          </td>
                          <td className="px-4 py-3 font-medium text-gray-800">
                            {drug.drug_name}
                          </td>
                          <td className={`px-4 py-3 text-right font-medium ${scoreColor(drug.overall_score)}`}>
                            {drug.overall_score.toFixed(3)}
                          </td>
                          <td className={`px-4 py-3 text-right ${scoreColor(drug.evidence_score)}`}>
                            {drug.evidence_score.toFixed(3)}
                          </td>
                          <td className={`px-4 py-3 text-right ${scoreColor(drug.sensitivity_score)}`}>
                            {drug.sensitivity_score.toFixed(3)}
                          </td>
                          <td className={`px-4 py-3 text-right ${scoreColor(1 - drug.resistance_score)}`}>
                            {drug.resistance_score.toFixed(3)}
                          </td>
                          <td className="px-4 py-3 text-gray-400 text-center">
                            {isExpanded ? '▲' : '▼'}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${drug.drug_name}-detail`}>
                            <td colSpan={7} className="px-6 py-4 bg-gray-50">
                              <div className="space-y-3">
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                  詳細理由（Explanations）
                                </h4>
                                {drug.explanations.length === 0 ? (
                                  <p className="text-sm text-gray-400">無詳細說明</p>
                                ) : (
                                  <div className="space-y-2">
                                    {drug.explanations.map((exp, i) => (
                                      <div
                                        key={i}
                                        className="bg-white rounded-lg border border-gray-100 p-3 text-sm"
                                      >
                                        <div className="flex items-start justify-between gap-4">
                                          <div className="space-y-1">
                                            <span className="inline-block rounded-full bg-primary-50 text-primary-700 text-xs font-medium px-2 py-0.5">
                                              {exp.category || 'general'}
                                            </span>
                                            <p className="text-gray-700 mt-1">
                                              {exp.detail}
                                            </p>
                                            {exp.source && (
                                              <p className="text-xs text-gray-400">
                                                來源：{exp.source}
                                              </p>
                                            )}
                                          </div>
                                          <span
                                            className={`text-xs font-medium whitespace-nowrap ${
                                              exp.score_impact >= 0
                                                ? 'text-green-600'
                                                : 'text-red-600'
                                            }`}
                                          >
                                            {exp.score_impact >= 0 ? '+' : ''}
                                            {exp.score_impact.toFixed(3)}
                                          </span>
                                        </div>
                                        {exp.trace_id && (
                                          <p className="text-xs text-gray-300 mt-1">
                                            trace: {exp.trace_id}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Raw JSON toggle */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <button
                onClick={() => setShowRawJson((v) => !v)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 transition"
              >
                <span>原始 Response JSON</span>
                <span className="text-gray-400">{showRawJson ? '▲' : '▼'}</span>
              </button>
              {showRawJson && (
                <pre className="px-4 pb-4 text-xs text-gray-600 overflow-x-auto">
                  {JSON.stringify(result, null, 2)}
                </pre>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

