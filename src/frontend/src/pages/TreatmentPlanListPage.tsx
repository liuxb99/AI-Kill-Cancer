import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DemoContextBanner, { useDemoContext } from '../components/DemoContextBanner'
import DualModeSelector from '../components/DualModeSelector'
import { getDatabasePatient, listRecentDatabasePatients, patientDisplayLabel, type DatabasePatient } from '../api/databasePatients'
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
function statusLabel(status: string): string { const labels: Record<string, string> = { draft: '草稿', proposed: '已提交', under_review: '審核中', approved: '已核准', active: '執行中', paused: '已暫停', completed: '已完成', cancelled: '已取消', superseded: '已取代' }; return labels[status?.toLowerCase()] || status || '—' }
function formatDateTime(iso: string): string { try { return new Date(iso).toLocaleString('zh-TW') } catch { return iso } }

export default function TreatmentPlanListPage() {
  const navigate = useNavigate()
  const demo = useDemoContext()
  const [patients, setPatients] = useState<DatabasePatient[]>([])
  const [patientId, setPatientId] = useState('')
  const [advancedPatientId, setAdvancedPatientId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [plans, setPlans] = useState<TreatmentPlanListItem[] | null>(null)
  const [skip, setSkip] = useState(0)
  const limit = 20

  useEffect(() => {
    if (demo.synthetic) { setLoading(false); return }
    async function load() {
      setLoading(true); setError(null)
      try {
        const response = await listRecentDatabasePatients(100)
        setPatients(response.items)
        const requested = new URLSearchParams(window.location.search).get('patientId')
        const initial = response.items.find((item) => item.patient_id === requested) || response.items[0]
        if (initial) await loadPlans(initial.patient_id, 0)
        else if (requested) { setAdvancedPatientId(requested); await selectAdvancedPatient(requested) }
      } catch (reason) { setError(reason instanceof Error ? reason.message : '無法載入患者資料') }
      finally { setLoading(false) }
    }
    void load()
  }, [demo.synthetic])

  async function loadPlans(id: string, nextSkip = 0) {
    const normalized = id.trim(); if (!normalized) return
    setPatientId(normalized); setLoading(true); setError(null)
    try { setPlans(await listTreatmentPlans(normalized, nextSkip, limit)); setSkip(nextSkip); const url = new URL(window.location.href); url.searchParams.set('patientId', normalized); window.history.replaceState({}, '', url) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '查詢 Treatment Plans 失敗') }
    finally { setLoading(false) }
  }
  async function selectAdvancedPatient(value: string) {
    const normalized = value.trim(); if (!normalized) return
    setLoading(true); setError(null)
    try { const patient = await getDatabasePatient(normalized); setPatients((current) => current.some((item) => item.patient_id === patient.patient_id) ? current : [patient, ...current].slice(0, 100)); await loadPlans(patient.patient_id, 0) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '患者不存在'); setLoading(false) }
  }

  const currentPage = Math.floor(skip / limit) + 1
  const recentContent = <div className="p-4">{loading && patients.length === 0 ? <p className="text-sm text-slate-500">載入患者資料中…</p> : patients.length === 0 ? <p className="text-sm text-slate-500">目前沒有可選擇的患者。</p> : <label className="block text-sm font-medium text-slate-700">最近 100 位患者<select aria-label="最近 100 位患者" className="mt-2 w-full rounded-lg border px-3 py-2" value={patientId} onChange={(event) => void loadPlans(event.target.value, 0)}>{patients.map((patient) => <option key={patient.patient_id} value={patient.patient_id}>{patientDisplayLabel(patient)}</option>)}</select></label>}{error && <p className="mt-3 text-sm text-red-600">{error}</p>}</div>

  return <main className="mx-auto max-w-6xl px-4 py-8">
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4"><div className="flex items-center gap-4"><button onClick={() => navigate(-1)} className="text-xl text-gray-400 hover:text-primary-600">←</button><div><p className="text-sm font-semibold text-primary-600">Treatment Plans</p><h1 className="text-3xl font-bold">治療計畫列表</h1><p className="mt-1 text-gray-600">正式模式顯示持久化 Treatment Plan；synthetic demo 模式展示同病例的研究流程草圖，不寫入正式計畫。</p></div></div>{!demo.synthetic && <button onClick={() => navigate(`/treatment-plans/new${patientId ? `?patientId=${encodeURIComponent(patientId)}` : ''}`)} className="rounded bg-green-600 px-5 py-2.5 text-sm font-medium text-white">＋建立新計畫</button>}</header>
    {demo.context && <DemoContextBanner context={demo.context} label="Synthetic Treatment Plan Context" />}
    {demo.context && <section className="rounded-xl border bg-white p-6 shadow-sm"><h2 className="text-lg font-bold">Synthetic treatment workflow preview</h2><div className="mt-4 grid gap-4 md:grid-cols-4"><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Case</div><strong>{demo.context.case_key}</strong></div><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Molecular finding</div><strong>{demo.context.variant.gene} {demo.context.variant.hgvs_p}</strong></div><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Candidate under review</div><strong>{demo.context.drug.name || '—'}</strong></div><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Evidence</div><strong>{demo.context.evidence.level || '—'}</strong></div></div><div className="mt-5 rounded-lg border border-dashed p-4 text-sm text-gray-600">流程：分子結果 → Evidence review → Clinical Decision → Tumor Board / safety review → Treatment Plan。Demo 不自動建立、核准或宣稱任何真實治療方案。</div></section>}
    {demo.synthetic && !demo.context && <p className="rounded border border-amber-200 bg-amber-50 p-4 text-sm">{demo.loading ? '載入 Demo Context…' : demo.error || '無 Demo Context'}</p>}
    {!demo.synthetic && <><DualModeSelector title="選擇治療計畫患者" description="最近 100 位患者與完整 Patient ID 查詢共用同一個計畫結果區。" recentContent={recentContent} advancedLabel="完整 Patient ID" advancedPlaceholder="輸入完整 UUID Patient ID" advancedValue={advancedPatientId} onAdvancedValueChange={setAdvancedPatientId} onAdvancedSubmit={() => selectAdvancedPatient(advancedPatientId)} advancedDisabled={!advancedPatientId.trim()} advancedLoading={loading} advancedHelp={error || '精準查詢成功後，會載入該患者的 Treatment Plans。'} />
    {plans !== null && plans.length === 0 && !loading && <section className="mt-6 rounded-xl border bg-white p-12 text-center text-gray-400">所選患者目前沒有 Treatment Plan。</section>}
    {plans !== null && plans.length > 0 && !loading && <section className="mt-6 space-y-4"><div className="overflow-hidden rounded-xl border bg-white shadow-sm"><div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs uppercase text-gray-500"><tr><th className="px-5 py-3">Plan ID</th><th className="px-5 py-3">Version</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Intent</th><th className="px-5 py-3">Current</th><th className="px-5 py-3">Created</th></tr></thead><tbody className="divide-y">{plans.map((plan) => <tr key={`${plan.plan_id}-v${plan.version}`} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/treatment-plans/${plan.plan_id}`)}><td className="px-5 py-3 font-mono text-xs">{plan.plan_id}</td><td className="px-5 py-3">v{plan.version}</td><td className="px-5 py-3"><span className={`rounded-full border px-2.5 py-0.5 text-xs ${statusColor(plan.plan_status)}`}>{statusLabel(plan.plan_status)}</span></td><td className="px-5 py-3">{plan.plan_intent || '—'}</td><td className="px-5 py-3">{plan.is_current ? <span className="font-medium text-green-600">✓ 當前</span> : '—'}</td><td className="px-5 py-3 text-xs text-gray-500">{formatDateTime(plan.created_at)}</td></tr>)}</tbody></table></div></div><div className="flex items-center justify-between text-sm text-gray-500"><span>第 {currentPage} 頁（每頁 {limit} 筆）</span><div className="flex gap-2"><button onClick={() => void loadPlans(patientId, skip - limit)} disabled={skip === 0 || loading} className="rounded border px-3 py-1 disabled:opacity-30">← 上一頁</button><button onClick={() => void loadPlans(patientId, skip + limit)} disabled={plans.length < limit || loading} className="rounded border px-3 py-1 disabled:opacity-30">下一頁 →</button></div></div></section>}</>}
  </main>
}
