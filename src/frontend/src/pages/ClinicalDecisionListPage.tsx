import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getDatabasePatient, listRecentDatabasePatients, patientDisplayLabel, type DatabasePatient } from '../api/databasePatients'
import { fetchClinicalDecisionsByPatientId, type ClinicalDecisionListResponse, type ClinicalDecisionResponse } from '../api/clinical_decision'
import DemoContextBanner, { useDemoContext } from '../components/DemoContextBanner'
import DualModeSelector from '../components/DualModeSelector'

function confidenceBadge(confidence: string): string {
  switch (confidence?.toLowerCase()) {
    case 'high': case 'very high': return 'bg-green-100 text-green-800 border-green-200'
    case 'medium': case 'moderate': return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'low': case 'very low': return 'bg-red-100 text-red-800 border-red-200'
    default: return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}
function formatDateTime(iso: string): string { try { return new Date(iso).toLocaleString('zh-TW') } catch { return iso } }

export default function ClinicalDecisionListPage() {
  const navigate = useNavigate()
  const demo = useDemoContext()
  const [patients, setPatients] = useState<DatabasePatient[]>([])
  const [patientId, setPatientId] = useState('')
  const [advancedValue, setAdvancedValue] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ClinicalDecisionListResponse | null>(null)

  useEffect(() => {
    if (demo.synthetic) { setLoading(false); return }
    async function load() {
      setLoading(true); setError(null)
      try {
        const response = await listRecentDatabasePatients(100)
        setPatients(response.items)
        const requested = new URLSearchParams(window.location.search).get('patientId')
        const initial = response.items.find((item) => item.patient_id === requested) || response.items[0]
        if (initial) await selectPatient(initial.patient_id)
        else if (requested) { setAdvancedValue(requested); await selectAdvancedPatient(requested) }
      } catch (reason) { setError(reason instanceof Error ? reason.message : '無法載入患者資料') }
      finally { setLoading(false) }
    }
    void load()
  }, [demo.synthetic])

  async function selectPatient(id: string) {
    const normalized = id.trim(); if (!normalized) return
    setPatientId(normalized); setLoading(true); setError(null); setResult(null)
    try { setResult(await fetchClinicalDecisionsByPatientId(normalized)); const url = new URL(window.location.href); url.searchParams.set('patientId', normalized); window.history.replaceState({}, '', url) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '查詢臨床決策失敗') }
    finally { setLoading(false) }
  }
  async function selectAdvancedPatient(value: string) {
    const normalized = value.trim(); if (!normalized) return
    setLoading(true); setError(null)
    try { const patient = await getDatabasePatient(normalized); setPatients((current) => current.some((item) => item.patient_id === patient.patient_id) ? current : [patient, ...current].slice(0, 100)); await selectPatient(patient.patient_id) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '患者不存在'); setLoading(false) }
  }

  const recentContent = <div className="divide-y">{patients.length === 0 && !loading ? <p className="p-6 text-center text-sm text-slate-500">目前沒有可供選擇的患者。</p> : patients.map((patient) => <button key={patient.patient_id} type="button" className={`block w-full px-4 py-3 text-left hover:bg-slate-50 ${patient.patient_id === patientId ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'}`} onClick={() => void selectPatient(patient.patient_id)}>{patientDisplayLabel(patient)}</button>)}</div>

  return <main className="mx-auto max-w-6xl px-4 py-8">
    <header className="mb-6 flex items-center gap-4"><button onClick={() => navigate(-1)} className="text-xl text-gray-400 hover:text-primary-600">←</button><div><p className="text-sm font-semibold text-primary-600">Clinical Decision</p><h1 className="text-3xl font-bold">臨床決策列表</h1><p className="mt-1 text-gray-600">正式模式查詢持久化資料；synthetic demo 模式則展示同一病例的決策脈絡，不寫入正式資料庫。</p></div></header>
    {demo.context && <DemoContextBanner context={demo.context} label="Synthetic Clinical Decision Context" />}
    {demo.context && <section className="rounded-xl border bg-white p-6 shadow-sm"><h2 className="text-lg font-bold">Synthetic decision preview</h2><div className="mt-4 grid gap-4 md:grid-cols-3"><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Variant</div><strong>{demo.context.variant.gene} {demo.context.variant.hgvs_p}</strong></div><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Evidence</div><strong>{demo.context.evidence.level} · {demo.context.evidence.direction}</strong></div><div className="rounded-lg bg-gray-50 p-4"><div className="text-xs text-gray-400">Drug under review</div><strong>{demo.context.drug.name || '—'}</strong></div></div><p className="mt-4 text-sm text-gray-600">此頁只展示「變異 → 證據 → 候選藥物 → 人工審查」工作流，不生成或宣稱真實臨床決策。</p></section>}
    {demo.synthetic && !demo.context && <p className="rounded border border-amber-200 bg-amber-50 p-4 text-sm">{demo.loading ? '載入 Demo Context…' : demo.error || '無 Demo Context'}</p>}
    {!demo.synthetic && <><DualModeSelector title="患者選擇" description="最近 100 位患者快速選擇，或查詢完整資料庫中的 Patient ID。" recentContent={recentContent} advancedLabel="完整 Patient ID" advancedPlaceholder="輸入完整 UUID Patient ID" advancedValue={advancedValue} onAdvancedValueChange={setAdvancedValue} onAdvancedSubmit={() => selectAdvancedPatient(advancedValue)} advancedLoading={loading} advancedHelp="進階模式會先確認患者存在，再使用相同結果區載入臨床決策。" />
    {error && <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">錯誤：{error}</p>}
    {!loading && result && result.decisions.length === 0 && <section className="mt-6 rounded-xl border bg-white p-12 text-center text-gray-400">所選患者目前沒有臨床決策記錄。</section>}
    {!loading && result && result.decisions.length > 0 && <section className="mt-6 overflow-hidden rounded-xl border bg-white shadow-sm"><div className="flex items-center justify-between border-b px-5 py-4"><h2 className="font-semibold">{patientId} 的決策</h2><span className="text-xs text-gray-400">最多展示 100 筆 · 共 {result.total ?? result.decisions.length} 筆</span></div><div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs uppercase text-gray-500"><tr><th className="px-5 py-3">決策類型</th><th className="px-5 py-3">信心等級</th><th className="px-5 py-3">Patient ID</th><th className="px-5 py-3">建立時間</th><th className="px-5 py-3">操作</th></tr></thead><tbody className="divide-y">{result.decisions.slice(0, 100).map((decision: ClinicalDecisionResponse) => <tr key={decision.decision_id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/clinical-decision/${decision.decision_id}`)}><td className="px-5 py-4 font-medium">{decision.decision_type || '—'}</td><td className="px-5 py-4"><span className={`rounded-full border px-2.5 py-0.5 text-xs ${confidenceBadge(decision.confidence)}`}>{decision.confidence || '—'}</span></td><td className="px-5 py-4 font-mono text-xs">{decision.patient_id || '—'}</td><td className="px-5 py-4 text-gray-500">{decision.created_at ? formatDateTime(decision.created_at) : '—'}</td><td className="px-5 py-4 text-primary-600">查看詳情 →</td></tr>)}</tbody></table></div></section>}</>}
  </main>
}
