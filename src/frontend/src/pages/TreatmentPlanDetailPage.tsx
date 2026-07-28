/**
 * TreatmentPlanDetailPage — Treatment Plan 明細頁面
 *
 * 功能：
 * 1. 從 URL 取得 plan_id
 * 2. 顯示完整 Plan 資訊
 * 3. 狀態操作按鈕（依目前狀態顯示可用操作）
 * 4. "Revise" 按鈕 → navigate 到 Revision Page
 *
 * 路由：請在 App.tsx 中加入 <Route path="/treatment-plans/:id" element={<TreatmentPlanDetailPage />} />
 */

import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getTreatmentPlan,
  getPlanVersions,
  getPlanTrace,
  submitPlan,
  approvePlan,
  activatePlan,
  pausePlan,
  completePlan,
  cancelPlan,
  revisePlan,
  type TreatmentPlanResponse,
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

function severityColor(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'high':
    case 'critical':
      return 'bg-red-100 text-red-700 border-red-200'
    case 'medium':
      return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'low':
      return 'bg-green-100 text-green-700 border-green-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
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

function renderArrayField(items: Record<string, any>[], emptyText = '無資料'): string {
  if (!items || items.length === 0) return emptyText
  return items.map((item, i) => JSON.stringify(item, null, 2)).join('\n---\n')
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function TreatmentPlanDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [plan, setPlan] = useState<TreatmentPlanResponse | null>(null)
  const [versions, setVersions] = useState<TreatmentPlanResponse[] | null>(null)
  const [trace, setTrace] = useState<Record<string, any>[] | null>(null)
  const [versionsLoading, setVersionsLoading] = useState(false)
  const [traceLoading, setTraceLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [showTrace, setShowTrace] = useState(false)

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
        if (!cancelled) setPlan(data)
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

    // 載入 versions
    setVersionsLoading(true)
    getPlanVersions(id)
      .then((data) => {
        if (!cancelled) setVersions(data)
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setVersionsLoading(false)
      })

    return () => { cancelled = true }
  }, [id])

  // ── Load trace on demand ────────────────────────────────────────────────

  const handleLoadTrace = async () => {
    if (!id || trace) {
      setShowTrace(!showTrace)
      return
    }
    setTraceLoading(true)
    try {
      const data = await getPlanTrace(id)
      setTrace(data)
      setShowTrace(true)
    } catch {
      setTrace([])
      setShowTrace(true)
    } finally {
      setTraceLoading(false)
    }
  }

  // ── State actions ──────────────────────────────────────────────────────

  const executeAction = async (action: string, actionFn: () => Promise<TreatmentPlanResponse>) => {
    setActionLoading(action)
    setActionError(null)
    try {
      const updated = await actionFn()
      setPlan(updated)
    } catch (e) {
      setActionError(e instanceof Error ? e.message : `${action} 操作失敗`)
    } finally {
      setActionLoading(null)
    }
  }

  const getAvailableActions = (status: string): Array<{ key: string; label: string; color: string; action: () => Promise<TreatmentPlanResponse> }> => {
    switch (status?.toLowerCase()) {
      case 'draft':
        return [{ key: 'submit', label: 'Submit (提交審核)', color: 'bg-blue-600 hover:bg-blue-700', action: () => submitPlan(id!) }]
      case 'proposed':
      case 'under_review':
        return [{ key: 'approve', label: 'Approve (核准)', color: 'bg-green-600 hover:bg-green-700', action: () => approvePlan(id!) }]
      case 'approved':
        return [
          { key: 'activate', label: 'Activate (啟動)', color: 'bg-emerald-600 hover:bg-emerald-700', action: () => activatePlan(id!) },
          { key: 'revise', label: 'Revise (修訂)', color: 'bg-orange-600 hover:bg-orange-700', action: () => Promise.reject(new Error('navigate')) },
        ]
      case 'active':
        return [
          { key: 'pause', label: 'Pause (暫停)', color: 'bg-purple-600 hover:bg-purple-700', action: () => pausePlan(id!) },
          { key: 'complete', label: 'Complete (完成)', color: 'bg-teal-600 hover:bg-teal-700', action: () => completePlan(id!) },
          { key: 'revise', label: 'Revise (修訂)', color: 'bg-orange-600 hover:bg-orange-700', action: () => Promise.reject(new Error('navigate')) },
        ]
      case 'paused':
        return [
          { key: 'activate', label: 'Resume (恢復)', color: 'bg-emerald-600 hover:bg-emerald-700', action: () => activatePlan(id!) },
        ]
      default:
        return []
    }
  }

  const handleAction = async (key: string, action: () => Promise<TreatmentPlanResponse>) => {
    if (key === 'revise') {
      navigate(`/treatment-plans/${id}/revise`)
      return
    }
    // Cancel is always available
    if (key === 'cancel') {
      await executeAction('cancel', () => cancelPlan(id!))
      return
    }
    await executeAction(key, action)
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
          <h1 className="text-xl font-bold text-primary-700">Treatment Plan 詳情</h1>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-6">
        {/* ── Loading State ──────────────────────────────────────────────── */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 space-y-4">
            <svg className="animate-spin h-10 w-10 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 0 00-4 4H4z" />
            </svg>
            <p className="text-sm text-gray-500">正在載入 Treatment Plan，請稍候…</p>
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
        {!loading && !error && !plan && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
            <p className="text-gray-400 text-lg">無 Treatment Plan 資料</p>
          </div>
        )}

        {/* ── Plan Detail ────────────────────────────────────────────────── */}
        {plan && !loading && (
          <>
            {/* Header info bar */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <h2 className="text-base font-semibold text-gray-800">Plan 詳情</h2>
                <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium border ${statusColor(plan.plan_status)}`}>
                  {statusLabel(plan.plan_status)}
                </span>
                <span className="text-xs text-gray-400 font-mono">v{plan.version}</span>
              </div>
              <div className="text-xs text-gray-400">
                {plan.created_at && <span>建立時間: {formatDateTime(plan.created_at)}</span>}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2">
              {getAvailableActions(plan.plan_status).map((btn) => (
                <button
                  key={btn.key}
                  onClick={() => handleAction(btn.key, btn.action)}
                  disabled={actionLoading !== null}
                  className={`${btn.color} disabled:opacity-50 text-white rounded-lg px-4 py-1.5 text-sm font-medium transition`}
                >
                  {actionLoading === btn.key ? '處理中…' : btn.label}
                </button>
              ))}
              {/* Cancel button (always available for non-terminal states) */}
              {!['completed', 'cancelled', 'superseded'].includes(plan.plan_status?.toLowerCase()) && (
                <button
                  onClick={() => handleAction('cancel', () => cancelPlan(id!))}
                  disabled={actionLoading !== null}
                  className="border border-red-300 text-red-600 hover:bg-red-50 rounded-lg px-4 py-1.5 text-sm font-medium transition disabled:opacity-50"
                >
                  {actionLoading === 'cancel' ? '處理中…' : 'Cancel (取消)'}
                </button>
              )}
            </div>

            {/* Action error */}
            {actionError && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-3 text-sm text-red-700">
                {actionError}
              </div>
            )}

            {/* ── Basic info grid ────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Plan ID</label>
                <p className="text-sm text-gray-700 font-mono">{plan.plan_id}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Patient ID</label>
                <p className="text-sm text-gray-700 font-mono">{plan.patient_id}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Consensus ID</label>
                <p className="text-sm text-gray-700 font-mono">{plan.consensus_id || '—'}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Clinical Decision ID</label>
                <p className="text-sm text-gray-700 font-mono">{plan.clinical_decision_id || '—'}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Recommendation ID</label>
                <p className="text-sm text-gray-700 font-mono">{plan.recommendation_id || '—'}</p>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Is Current</label>
                <p className="text-sm text-gray-700">{plan.is_current ? '✓ 當前版本' : '— 非當前版本'}</p>
              </div>
              {plan.previous_plan_id && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Previous Plan ID</label>
                  <p className="text-sm text-gray-700 font-mono">{plan.previous_plan_id}</p>
                </div>
              )}
              {plan.supersedes_plan_id && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Supersedes Plan ID</label>
                  <p className="text-sm text-gray-700 font-mono">{plan.supersedes_plan_id}</p>
                </div>
              )}
            </div>

            {/* Intent & Goals */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">治療意圖 (Plan Intent)</label>
              <p className="text-sm text-gray-700">{plan.plan_intent || '—'}</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">治療目標 (Treatment Goals)</label>
              {plan.treatment_goals && plan.treatment_goals.length > 0 ? (
                <ul className="space-y-1.5">
                  {plan.treatment_goals.map((g, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-gray-300 mt-0.5">•</span>
                      <span>{g}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-400">無治療目標</p>
              )}
            </div>

            {/* Summary */}
            {plan.summary && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">摘要 (Summary)</label>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{plan.summary}</p>
              </div>
            )}

            {/* Clinical Rationale */}
            {plan.clinical_rationale && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">臨床理由 (Clinical Rationale)</label>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{plan.clinical_rationale}</p>
              </div>
            )}

            {/* Revision Reason */}
            {plan.revision_reason && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">修訂理由 (Revision Reason)</label>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{plan.revision_reason}</p>
              </div>
            )}

            {/* ── Phases ──────────────────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">治療階段 (Phases)</h3>
              </div>
              {plan.phases && plan.phases.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {plan.phases.map((phase: any, i: number) => (
                    <details key={i} className="group">
                      <summary className="px-5 py-3 cursor-pointer text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2">
                        <span className="text-primary-600">▶</span>
                        {phase.name || `Phase ${i + 1}`}
                        {phase.phase_type && <span className="text-xs text-gray-400 ml-2">({phase.phase_type})</span>}
                        {phase.status && (
                          <span className={`ml-auto inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${statusColor(phase.status)}`}>
                            {statusLabel(phase.status)}
                          </span>
                        )}
                      </summary>
                      <div className="px-5 py-3 bg-gray-50 space-y-2 text-sm">
                        {phase.description && <p className="text-gray-600">{phase.description}</p>}
                        {phase.duration_days && <p className="text-gray-500">持續時間: {phase.duration_days} 天</p>}
                        {phase.planned_start && <p className="text-gray-500">預計開始: {formatDateTime(phase.planned_start)}</p>}
                        {phase.planned_end && <p className="text-gray-500">預計結束: {formatDateTime(phase.planned_end)}</p>}
                        {phase.items && phase.items.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Items:</p>
                            <div className="space-y-1">
                              {phase.items.map((item: any, j: number) => (
                                <div key={j} className="bg-white rounded border border-gray-200 p-2 text-xs">
                                  {item.name && <span className="font-medium">{item.name}</span>}
                                  {item.item_type && <span className="text-gray-400 ml-1">({item.item_type})</span>}
                                  {item.description && <p className="text-gray-500 mt-0.5">{item.description}</p>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              ) : (
                <div className="px-5 py-4 text-sm text-gray-400">無治療階段</div>
              )}
            </div>

            {/* ── Items ──────────────────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">治療項目 (Items)</h3>
              </div>
              {plan.items && plan.items.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {plan.items.map((item: any, i: number) => (
                    <div key={i} className="px-5 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-700">{item.name || '—'}</span>
                        {item.item_type && <span className="text-xs text-gray-400">({item.item_type})</span>}
                        {item.status && (
                          <span className={`ml-auto inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${statusColor(item.status)}`}>
                            {statusLabel(item.status)}
                          </span>
                        )}
                      </div>
                      {item.description && <p className="text-gray-500 mt-1 text-xs">{item.description}</p>}
                      {(item.drug_id || item.frequency || item.duration || item.route) && (
                        <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400">
                          {item.drug_id && <span>Drug ID: {item.drug_id}</span>}
                          {item.frequency && <span>頻率: {item.frequency}</span>}
                          {item.duration && <span>持續: {item.duration}</span>}
                          {item.route && <span>途徑: {item.route}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="px-5 py-4 text-sm text-gray-400">無治療項目</div>
              )}
            </div>

            {/* ── Monitoring Schedule ────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">監測排程 (Monitoring Schedule)</label>
              {plan.monitoring && plan.monitoring.length > 0 ? (
                <div className="space-y-2">
                  {plan.monitoring.map((m: any, i: number) => (
                    <div key={i} className="bg-gray-50 rounded-lg border border-gray-100 p-3 text-sm">
                      <div className="font-medium text-gray-700">{m.name || m.monitoring_type || `Monitoring #${i + 1}`}</div>
                      {m.schedule && <div className="text-xs text-gray-500 mt-1">排程: {m.schedule}</div>}
                      {m.frequency && <div className="text-xs text-gray-500">頻率: {m.frequency}</div>}
                      {m.interval && <div className="text-xs text-gray-500">間隔: {m.interval}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無監測排程</p>
              )}
            </div>

            {/* ── Safety Rules ────────────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">安全規則 (Safety Rules)</label>
              {plan.safety_rules && plan.safety_rules.length > 0 ? (
                <div className="space-y-2">
                  {plan.safety_rules.map((rule: any, i: number) => (
                    <div key={i} className="rounded-lg border p-3 text-sm" style={{
                      backgroundColor: rule.severity?.toLowerCase() === 'high' ? '#fef2f2' : rule.severity?.toLowerCase() === 'medium' ? '#fffbeb' : '#f0fdf4',
                      borderColor: rule.severity?.toLowerCase() === 'high' ? '#fecaca' : rule.severity?.toLowerCase() === 'medium' ? '#fde68a' : '#bbf7d0',
                    }}>
                      <div className="flex items-center gap-2">
                        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${severityColor(rule.severity)}`}>
                          {rule.severity || '—'}
                        </span>
                        <span className="font-medium text-gray-700">{rule.rule_type || `Rule #${i + 1}`}</span>
                      </div>
                      {rule.condition && <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap">{JSON.stringify(rule.condition, null, 2)}</pre>}
                      {rule.recommended_action && <p className="text-xs text-gray-500 mt-1">建議動作: {rule.recommended_action}</p>}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無安全規則</p>
              )}
            </div>

            {/* ── Alternatives ────────────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">替代方案 (Alternatives)</label>
              {plan.alternatives && plan.alternatives.length > 0 ? (
                <div className="space-y-2">
                  {plan.alternatives.map((alt, i) => (
                    <div key={i} className="bg-gray-50 rounded-lg border border-gray-100 p-3 text-sm">
                      <pre className="text-gray-700 text-xs overflow-x-auto whitespace-pre-wrap">{JSON.stringify(alt, null, 2)}</pre>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無替代方案</p>
              )}
            </div>

            {/* ── Approval Info ────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {plan.created_by && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">建立者 (Created By)</label>
                  <p className="text-sm text-gray-700 font-mono">{plan.created_by}</p>
                </div>
              )}
              {plan.approved_by && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">核准者 (Approved By)</label>
                  <p className="text-sm text-gray-700 font-mono">{plan.approved_by}</p>
                </div>
              )}
              {plan.approved_at && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">核准時間</label>
                  <p className="text-sm text-gray-700">{formatDateTime(plan.approved_at)}</p>
                </div>
              )}
              {(plan as any).review_date && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">審查日期 (Review Date)</label>
                  <p className="text-sm text-gray-700">{formatDateTime((plan as any).review_date)}</p>
                </div>
              )}
              {plan.activated_at && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">啟用時間</label>
                  <p className="text-sm text-gray-700">{formatDateTime(plan.activated_at)}</p>
                </div>
              )}
            </div>

            {/* ── Trace / Calculation Steps ──────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <button
                onClick={handleLoadTrace}
                className="text-xs font-medium text-gray-500 uppercase tracking-wider hover:text-primary-600 transition"
              >
                {showTrace ? '隐藏' : '顯示'} 推理軌跡 (Trace / Calculation Steps)
              </button>
              {showTrace && (
                <div className="mt-3">
                  {traceLoading ? (
                    <p className="text-sm text-gray-400">載入中…</p>
                  ) : trace && trace.length > 0 ? (
                    <pre className="text-xs text-gray-700 bg-gray-50 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {JSON.stringify(trace, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-sm text-gray-400">無推理軌跡</p>
                  )}
                </div>
              )}
            </div>

            {/* ── Versions ────────────────────────────────────────────────── */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">版本歷史 (Versions)</label>
              {versionsLoading ? (
                <p className="text-sm text-gray-400">載入中…</p>
              ) : versions && versions.length > 0 ? (
                <div className="space-y-2">
                  {versions.map((v, i) => (
                    <div
                      key={`${v.plan_id}-v${v.version}`}
                      className="flex items-center justify-between bg-gray-50 rounded-lg p-3 cursor-pointer hover:bg-gray-100 transition"
                      onClick={() => navigate(`/treatment-plans/${v.plan_id}`)}
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-medium text-gray-700">v{v.version}</span>
                        <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium border ${statusColor(v.plan_status)}`}>
                          {statusLabel(v.plan_status)}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {formatDateTime(v.created_at)}
                        {v.is_current && <span className="ml-2 text-green-600 font-medium">當前</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">無其他版本</p>
              )}
            </div>

            {/* ── Knowledge Graph Link ────────────────────────────────────── */}
            {plan.patient_id && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <a
                  href={`/clinical-graph?patientId=${plan.patient_id}`}
                  className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-800"
                >
                  🔗 View in Knowledge Graph &rarr;
                </a>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
