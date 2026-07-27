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
import { createTumorBoardConsensus, type SpecialistOpinion } from '../api/workbench'

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

  const handleOpinionChange = (index: number, field: string, value: string | number | boolean) => {
    const updated = [...specialistOpinions]
    ;(updated[index] as any)[field] = value
    setSpecialistOpinions(updated)
  }

  const addOpinionRow = () => {
    setSpecialistOpinions([...specialistOpinions, { specialty: 'medical_oncology', position: 'support', confidence: 0.8, rationale: '' }])
  }

  const removeOpinionRow = (index: number) => {
    if (specialistOpinions.length <= 1) return
    setSpecialistOpinions(specialistOpinions.filter((_, i) => i !== index))
  }

  const handleCreateConsensus = async () => {
    if (!decision) return
    setConsensusCreating(true)
    setConsensusError(null)
    try {
      const result = await createTumorBoardConsensus({
        patient_id: decision.patient_id,
        recommendation_id: decision.recommendation_id || '',
        clinical_decision_id: decision.decision_id || '',
        specialist_opinions: specialistOpinions,
      })
      navigate(`/tumor-board/${result.consensus_id}`)
    } catch (err: any) {
      setConsensusError(err.message || '建立共識失敗')
    } finally {
      setConsensusCreating(false)
    }
  }

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [decision, setDecision] = useState<ClinicalDecisionResponse | null>(null)
  const [showConsensusForm, setShowConsensusForm] = useState(false)
  const [consensusCreating, setConsensusCreating] = useState(false)
  const [consensusError, setConsensusError] = useState<string | null>(null)
  const [specialistOpinions, setSpecialistOpinions] = useState<SpecialistOpinion[]>([
    { specialty: 'medical_oncology', position: 'support', confidence: 0.8, rationale: '' },
  ])

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
                {decision.patient_id && (
                  <a
                    href={`/clinical-graph?patientId=${decision.patient_id}`}
                    className="inline-flex items-center gap-1 mt-2 text-xs text-primary-600 hover:text-primary-800"
                  >
                    View in Knowledge Graph &rarr;
                  </a>
                )}
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

            {/* ── Tumor Board Consensus Section ────────────────────────────── */}
            {decision && (
              <div className="mt-8 border-t border-gray-200 pt-6">
                <button
                  onClick={() => setShowConsensusForm(!showConsensusForm)}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition text-sm font-medium"
                >
                  {showConsensusForm ? '取消' : '建立腫瘤委員會共識'}
                </button>

                {showConsensusForm && (
                  <div className="mt-4 space-y-4">
                    <h3 className="text-base font-semibold text-gray-800">專家意見</h3>

                    {consensusError && (
                      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
                        {consensusError}
                      </div>
                    )}

                    {specialistOpinions.map((opinion, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-gray-500">意見 #{index + 1}</span>
                          {specialistOpinions.length > 1 && (
                            <button onClick={() => removeOpinionRow(index)} className="text-xs text-red-500 hover:text-red-700">
                              移除
                            </button>
                          )}
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">專科</label>
                            <select
                              value={opinion.specialty}
                              onChange={(e) => handleOpinionChange(index, 'specialty', e.target.value)}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                            >
                              <option value="medical_oncology">腫瘤內科</option>
                              <option value="surgical_oncology">腫瘤外科</option>
                              <option value="radiation_oncology">放射腫瘤科</option>
                              <option value="pathology">病理科</option>
                              <option value="radiology">放射科</option>
                              <option value="genomics">基因組學</option>
                              <option value="pharmacy">藥學</option>
                              <option value="nursing">護理</option>
                              <option value="palliative_care">安寧緩和</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">立場</label>
                            <select
                              value={opinion.position}
                              onChange={(e) => handleOpinionChange(index, 'position', e.target.value)}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                            >
                              <option value="support">支持</option>
                              <option value="oppose">反對</option>
                              <option value="abstain">棄權</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">信心度: {opinion.confidence}</label>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.1"
                              value={opinion.confidence}
                              onChange={(e) => handleOpinionChange(index, 'confidence', parseFloat(e.target.value))}
                              className="w-full"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">參與者 ID（選填）</label>
                            <input
                              type="text"
                              value={opinion.participant_id || ''}
                              onChange={(e) => handleOpinionChange(index, 'participant_id', e.target.value)}
                              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                              placeholder="optional"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">理由（選填）</label>
                          <textarea
                            value={opinion.rationale || ''}
                            onChange={(e) => handleOpinionChange(index, 'rationale', e.target.value)}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                            rows={2}
                            placeholder="請說明此意見的理由..."
                          />
                        </div>
                      </div>
                    ))}

                    <div className="flex gap-3">
                      <button
                        onClick={addOpinionRow}
                        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                      >
                        + 新增意見
                      </button>
                      <button
                        onClick={handleCreateConsensus}
                        disabled={consensusCreating}
                        className="px-4 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                      >
                        {consensusCreating ? '建立中…' : '提交共識'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
