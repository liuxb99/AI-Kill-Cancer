import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DualModeSelector from '../components/DualModeSelector'
import {
  getDatabasePatient,
  listRecentDatabasePatients,
  patientDisplayLabel,
  type DatabasePatient,
} from '../api/databasePatients'
import { listTreatmentPlans, type TreatmentPlanListItem } from '../api/treatmentPlan'

function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'draft': return 'bg-gray-100 text-gray-700 border-gray-200'
    case 'proposed': return 'bg-blue-100 text-blue-700 border-blue-200'
    case 'under_review': return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'approved': return 'bg-green-100 text-green-700 border-green-200'
    case 'active': return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'paused': return 'bg-purple-100 text-purple-700 border-purple-200'
    case 'completed': return 'bg-teal-100 text-teal-700 border-teal-200'
    case 'cancelled': return 'bg-red-100 text-red-700 border-red-200'
    case 'superseded': return 'bg-orange-100 text-orange-700 border-orange-200'
    default: return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: '草稿', proposed: '已提交', under_review: '審核中', approved: '已核准',
    active: '執行中', paused: '已暫停', completed: '已完成', cancelled: '已取消', superseded: '已取代',
  }
  return labels[status?.toLowerCase()] || status || '—'
}

function formatDateTime(iso: string): string {
  try { return new Date(iso).toLocaleString('zh-TW') } catch { return iso }
}

export default function TreatmentPlanListPage() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<DatabasePatient[]>([])
  const [patientId, setPatientId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [plans, setPlans] = useState<TreatmentPlanListItem[] | null>(null)
  const [skip, setSkip] = useState(0)
  const limit = 20

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await listRecentDatabasePatients(100)
        setPatients(response.items)
        const requested = new URLSearchParams(window.location.search).get('patientId')
        const initial = response.items.find((item) => item.patient_id === requested) || response.items[0]
        if (initial) await selectPatient(initial.patient_id)
        else if (requested) await selectAdvancedPatient(requested)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '無法載入患者資料')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  async function loadPlans(id: string, nextSkip = 0) {
    const normalized = id.trim()
    if (!normalized) return
    setPatientId(normalized)
    setLoading(true)
    setError(null)
    try {
      setPlans(await listTreatmentPlans(normalized, nextSkip, limit))
      setSkip(nextSkip)
      const url = new URL(window.location.href)
      url.searchParams.set('patientId', normalized)
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '查詢 Treatment Plans 失敗')
    } finally {
      setLoading(false)
    }
  }

  async function selectPatient(id: string) {
    await loadPlans(id, 0)
  }

  async function selectAdvancedPatient(value: string) {
    const normalized = value.trim()
    if (!normalized) return
    setLoading(true)
    setError(null)
    try {
      const patient = await getDatabasePatient(normalized)
      setPatients((current) => current.some((item) => item.patient_id === patient.patient_id) ? current : [patient, ...current].slice(0, 100))
      await loadPlans(patient.patient_id, 0)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '患者不存在')
      setLoading(false)
    }
  }

  const currentPage = Math.floor(skip / limit) + 1

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4"><button onClick={() => navigate(-1)} className="text-xl text-gray-400 hover:text-primary-600">←</button><div><p className="text-sm font-semibold text-primary-600">Treatment Plans</p><h1 className="text-3xl font-bold">治療計畫列表</h1><p className="mt-1 text-gray-600">最近 100 位患者快速選擇，或以完整 Patient ID 精準查詢。</p></div></div>
        <button onClick={() => navigate(`/treatment-plans/new${patientId ? `?patientId=${encodeURIComponent(patientId)}` : ''}`)} className="rounded bg-green-600 px-5 py-2.5 text-sm font-medium text-white">＋建立新計畫</button>
      </header>

      <DualModeSelector
        items={patients}
        selectedId={patientId}
        onSelect={(id) => void selectPatient(id)}
        getId={(item) => item.patient_id}
        getLabel={patientDisplayLabel}
        listLabel="最近 100 位患者"
        queryLabel="完整 Patient ID"
        queryPlaceholder="輸入完整 UUID Patient ID"
        onAdvancedQuery={selectAdvancedPatient}
        loading={loading}
        error={error}
      />

      {plans !== null && plans.length === 0 && !loading && <section className="mt-6 rounded-xl border bg-white p-12 text-center text-gray-400">所選患者目前沒有 Treatment Plan。</section>}

      {plans !== null && plans.length > 0 && !loading && (
        <section className="mt-6 space-y-4">
          <div className="overflow-hidden rounded-xl border bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs uppercase text-gray-500"><tr><th className="px-5 py-3">Plan ID</th><th className="px-5 py-3">Version</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Intent</th><th className="px-5 py-3">Current</th><th className="px-5 py-3">Created</th></tr></thead><tbody className="divide-y">{plans.map((plan) => <tr key={`${plan.plan_id}-v${plan.version}`} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/treatment-plans/${plan.plan_id}`)}><td className="px-5 py-3 font-mono text-xs">{plan.plan_id}</td><td className="px-5 py-3">v{plan.version}</td><td className="px-5 py-3"><span className={`rounded-full border px-2.5 py-0.5 text-xs ${statusColor(plan.plan_status)}`}>{statusLabel(plan.plan_status)}</span></td><td className="px-5 py-3">{plan.plan_intent || '—'}</td><td className="px-5 py-3">{plan.is_current ? <span className="font-medium text-green-600">✓ 當前</span> : '—'}</td><td className="px-5 py-3 text-xs text-gray-500">{formatDateTime(plan.created_at)}</td></tr>)}</tbody></table></div></div>
          <div className="flex items-center justify-between text-sm text-gray-500"><span>第 {currentPage} 頁（每頁 {limit} 筆）</span><div className="flex gap-2"><button onClick={() => void loadPlans(patientId, skip - limit)} disabled={skip === 0 || loading} className="rounded border px-3 py-1 disabled:opacity-30">← 上一頁</button><button onClick={() => void loadPlans(patientId, skip + limit)} disabled={plans.length < limit || loading} className="rounded border px-3 py-1 disabled:opacity-30">下一頁 →</button></div></div>
        </section>
      )}
    </main>
  )
}
