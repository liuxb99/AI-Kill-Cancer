/**
 * TreatmentPlanCreatePage — 建立 Treatment Plan 頁面
 *
 * 功能：
 * 1. 從 URL query parameter 接收 consensus_id（從 TumorBoardConsensusPage 跳轉）
 * 2. 載入 Consensus + Clinical Decision + Recommendation 上游資料
 * 3. 表單：plan_intent, treatment_goals, clinical_context
 * 4. 自動驗證上游 ID 一致性
 * 5. 提交成功 → navigate 到 Detail
 *
 * 路由：請在 App.tsx 中加入 <Route path="/treatment-plans/new" element={<TreatmentPlanCreatePage />} />
 */

import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getTumorBoardConsensus, type TumorBoardConsensus } from '../api/workbench'
import { createTreatmentPlan, type CreateTreatmentPlanRequest } from '../api/treatmentPlan'

// ─── Helpers ─────────────────────────────────────────────────────────────────

const INTENT_OPTIONS = [
  { value: 'curative', label: '根治性 (Curative)' },
  { value: 'palliative', label: '緩和性 (Palliative)' },
  { value: 'adjuvant', label: '輔助性 (Adjuvant)' },
  { value: 'neoadjuvant', label: '新輔助性 (Neoadjuvant)' },
  { value: 'maintenance', label: '維持性 (Maintenance)' },
  { value: 'preventive', label: '預防性 (Preventive)' },
  { value: 'diagnostic', label: '診斷性 (Diagnostic)' },
  { value: 'supportive', label: '支持性 (Supportive)' },
]

// ─── Main Component ──────────────────────────────────────────────────────────

export default function TreatmentPlanCreatePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const consensusId = searchParams.get('consensus_id') || ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [consensus, setConsensus] = useState<TumorBoardConsensus | null>(null)

  // Form fields
  const [planIntent, setPlanIntent] = useState('curative')
  const [treatmentGoals, setTreatmentGoals] = useState<string[]>([''])
  const [clinicalContext, setClinicalContext] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!consensusId) {
      setError('缺少 Consensus ID，請從腫瘤委員會共識頁面跳轉')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    getTumorBoardConsensus(consensusId)
      .then((data) => {
        if (!cancelled) {
          setConsensus(data)
          // 預填 clinical_context 資訊
          const ctxParts: string[] = []
          if (data.final_recommendation) ctxParts.push(`Final Recommendation: ${data.final_recommendation}`)
          if (data.supporting_rationale) ctxParts.push(`Rationale: ${data.supporting_rationale}`)
          if (data.required_follow_up?.length) ctxParts.push(`Follow-up: ${data.required_follow_up.join('; ')}`)
          setClinicalContext(ctxParts.join('\n'))
        }
      })
      .catch((e) => {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : '載入 Consensus 失敗'
          if (msg.includes('404') || msg.includes('Not Found')) {
            setError('找不到此 Consensus 記錄')
          } else {
            setError(msg)
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [consensusId])

  // ── Goal handlers ──────────────────────────────────────────────────────

  const handleGoalChange = (index: number, value: string) => {
    const updated = [...treatmentGoals]
    updated[index] = value
    setTreatmentGoals(updated)
  }

  const addGoal = () => {
    setTreatmentGoals([...treatmentGoals, ''])
  }

  const removeGoal = (index: number) => {
    if (treatmentGoals.length <= 1) return
    setTreatmentGoals(treatmentGoals.filter((_, i) => i !== index))
  }

  // ── Validation ─────────────────────────────────────────────────────────

  const validate = (): boolean => {
    const errors: Record<string, string> = {}
    const filteredGoals = treatmentGoals.map((g) => g.trim()).filter(Boolean)

    if (!planIntent) errors.planIntent = '請選擇治療意圖'
    if (filteredGoals.length === 0) errors.treatmentGoals = '請填寫至少一個治療目標'
    if (!clinicalContext.trim()) errors.clinicalContext = '請填寫臨床背景資訊'

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  // ── Submit ─────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    if (!consensus) return

    setSubmitting(true)
    setError(null)

    try {
      const payload: CreateTreatmentPlanRequest = {
        patient_id: consensus.patient_id,
        recommendation_id: consensus.recommendation_id,
        clinical_decision_id: consensus.clinical_decision_id,
        consensus_id: consensus.consensus_id,
        plan_intent: planIntent,
        treatment_goals: treatmentGoals.map((g) => g.trim()).filter(Boolean),
        clinical_context: {
          cancer_type: '',
          stage: '',
          histology: '',
          clinical_notes: clinicalContext.trim(),
        },
      }

      const result = await createTreatmentPlan(payload)
      navigate(`/treatment-plans/${result.plan_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '建立 Treatment Plan 失敗')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────

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
          <h1 className="text-xl font-bold text-primary-700">建立 Treatment Plan</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* ── Loading State ──────────────────────────────────────────────── */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <svg
              className="animate-spin h-10 w-10 text-primary-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 0 00-4 4H4z" />
            </svg>
            <p className="text-sm text-gray-500">正在載入上游資料，請稍候…</p>
          </div>
        )}

        {/* ── Error State ────────────────────────────────────────────────── */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
            <span className="font-medium">錯誤：</span>
            {error}
          </div>
        )}

        {/* ── Consensus Info (read-only) ──────────────────────────────────── */}
        {consensus && !loading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 mb-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">上游 Consensus 資訊</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500 text-xs uppercase tracking-wider">Consensus ID</span>
                <p className="font-mono text-gray-700">{consensus.consensus_id}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs uppercase tracking-wider">Patient ID</span>
                <p className="font-mono text-gray-700">{consensus.patient_id}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs uppercase tracking-wider">Clinical Decision ID</span>
                <p className="font-mono text-gray-700">{consensus.clinical_decision_id}</p>
              </div>
              <div>
                <span className="text-gray-500 text-xs uppercase tracking-wider">Recommendation ID</span>
                <p className="font-mono text-gray-700">{consensus.recommendation_id}</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Create Form ────────────────────────────────────────────────── */}
        {consensus && !loading && (
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
            {/* Plan Intent */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                治療意圖 (Plan Intent) <span className="text-red-500">*</span>
              </label>
              <select
                value={planIntent}
                onChange={(e) => setPlanIntent(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {INTENT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {fieldErrors.planIntent && (
                <p className="text-xs text-red-500 mt-1">{fieldErrors.planIntent}</p>
              )}
            </div>

            {/* Treatment Goals */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                治療目標 (Treatment Goals) <span className="text-red-500">*</span>
              </label>
              <div className="space-y-2">
                {treatmentGoals.map((goal, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={goal}
                      onChange={(e) => handleGoalChange(i, e.target.value)}
                      placeholder={`治療目標 ${i + 1}`}
                      className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    {treatmentGoals.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeGoal(i)}
                        className="text-red-400 hover:text-red-600 text-sm"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addGoal}
                className="mt-2 text-sm text-primary-600 hover:text-primary-800"
              >
                + 新增目標
              </button>
              {fieldErrors.treatmentGoals && (
                <p className="text-xs text-red-500 mt-1">{fieldErrors.treatmentGoals}</p>
              )}
            </div>

            {/* Clinical Context */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                臨床背景 (Clinical Context) <span className="text-red-500">*</span>
              </label>
              <textarea
                value={clinicalContext}
                onChange={(e) => setClinicalContext(e.target.value)}
                rows={5}
                placeholder="請輸入臨床背景資訊、治療理由、注意事項等…"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {fieldErrors.clinicalContext && (
                <p className="text-xs text-red-500 mt-1">{fieldErrors.clinicalContext}</p>
              )}
            </div>

            {/* Submit */}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white rounded-lg px-6 py-2.5 text-sm font-medium transition"
              >
                {submitting ? '建立中…' : '建立 Treatment Plan'}
              </button>
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="border border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg px-6 py-2.5 text-sm font-medium transition"
              >
                取消
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  )
}
