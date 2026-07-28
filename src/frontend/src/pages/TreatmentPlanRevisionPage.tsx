/**
 * TreatmentPlanRevisionPage — Treatment Plan 修訂頁面
 *
 * 功能：
 * 1. 載入現有 Plan 作為預設值
 * 2. 可修改 plan_intent, treatment_goals, clinical_context
 * 3. 顯示 revision_reason 輸入框（必填）
 * 4. 提交成功 → navigate 到新版本的 Detail
 *
 * 路由：請在 App.tsx 中加入 <Route path="/treatment-plans/:id/revise" element={<TreatmentPlanRevisionPage />} />
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getTreatmentPlan,
  revisePlan,
  type TreatmentPlanResponse,
} from '../api/treatmentPlan'

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

export default function TreatmentPlanRevisionPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [plan, setPlan] = useState<TreatmentPlanResponse | null>(null)

  // Form fields
  const [planIntent, setPlanIntent] = useState('curative')
  const [treatmentGoals, setTreatmentGoals] = useState<string[]>([''])
  const [clinicalContext, setClinicalContext] = useState('')
  const [revisionReason, setRevisionReason] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!id) {
      setError('缺少 Plan ID')
      setLoading(false)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    getTreatmentPlan(id)
      .then((data) => {
        if (!cancelled) {
          setPlan(data)
          // 預填表單
          setPlanIntent(data.plan_intent || 'curative')
          setTreatmentGoals(data.treatment_goals?.length ? data.treatment_goals : [''])
          // 從 clinical_rationale 或 summary 提取臨床背景
          setClinicalContext(data.clinical_rationale || data.summary || '')
        }
      })
      .catch((e) => {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : '載入 Treatment Plan 失敗'
          if (msg.includes('404') || msg.includes('Not Found')) {
            setError('找不到此 Treatment Plan')
          } else {
            setError(msg)
          }
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [id])

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
    if (!revisionReason.trim()) errors.revisionReason = '請填寫修訂理由（必填）'

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  // ── Submit ─────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    if (!id) return

    setSubmitting(true)
    setError(null)

    try {
      const result = await revisePlan(id, {
        plan_intent: planIntent,
        treatment_goals: treatmentGoals.map((g) => g.trim()).filter(Boolean),
        clinical_context: {
          cancer_type: '',
          stage: '',
          histology: '',
          clinical_notes: clinicalContext.trim(),
        },
        revision_reason: revisionReason.trim(),
      })
      navigate(`/treatment-plans/${result.plan_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '修訂 Treatment Plan 失敗')
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
          <h1 className="text-xl font-bold text-primary-700">修訂 Treatment Plan</h1>
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
            <p className="text-sm text-gray-500">正在載入現有 Plan，請稍候…</p>
          </div>
        )}

        {/* ── Error State ────────────────────────────────────────────────── */}
        {error && !loading && !submitting && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-sm text-red-700">
            <span className="font-medium">錯誤：</span>
            {error}
          </div>
        )}

        {/* ── Revision Form ────────────────────────────────────────────────── */}
        {plan && !loading && (
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">
            {/* Current Plan Info (read-only) */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">目前 Plan 資訊（唯讀）</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-gray-500">Plan ID:</span> <span className="font-mono">{plan.plan_id}</span></div>
                <div><span className="text-gray-500">Version:</span> <span className="font-mono">v{plan.version}</span></div>
                <div><span className="text-gray-500">Status:</span> <span>{plan.plan_status}</span></div>
                <div><span className="text-gray-500">Is Current:</span> <span>{plan.is_current ? '✓' : '—'}</span></div>
              </div>
            </div>

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
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              {fieldErrors.planIntent && <p className="text-xs text-red-500 mt-1">{fieldErrors.planIntent}</p>}
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
                      <button type="button" onClick={() => removeGoal(i)} className="text-red-400 hover:text-red-600 text-sm">✕</button>
                    )}
                  </div>
                ))}
              </div>
              <button type="button" onClick={addGoal} className="mt-2 text-sm text-primary-600 hover:text-primary-800">
                + 新增目標
              </button>
              {fieldErrors.treatmentGoals && <p className="text-xs text-red-500 mt-1">{fieldErrors.treatmentGoals}</p>}
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
              {fieldErrors.clinicalContext && <p className="text-xs text-red-500 mt-1">{fieldErrors.clinicalContext}</p>}
            </div>

            {/* Revision Reason */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                修訂理由 (Revision Reason) <span className="text-red-500">*</span>
              </label>
              <textarea
                value={revisionReason}
                onChange={(e) => setRevisionReason(e.target.value)}
                rows={3}
                placeholder="請說明修訂的原因..."
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {fieldErrors.revisionReason && <p className="text-xs text-red-500 mt-1">{fieldErrors.revisionReason}</p>}
            </div>

            {/* Submit */}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="bg-orange-600 hover:bg-orange-700 disabled:bg-orange-300 text-white rounded-lg px-6 py-2.5 text-sm font-medium transition"
              >
                {submitting ? '提交修訂中…' : '提交修訂'}
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
