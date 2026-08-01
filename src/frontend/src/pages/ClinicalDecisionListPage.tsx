import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import DualModeSelector from '../components/DualModeSelector'
import {
  getDatabasePatient,
  listRecentDatabasePatients,
  patientDisplayLabel,
  type DatabasePatient,
} from '../api/databasePatients'
import {
  fetchClinicalDecisionsByPatientId,
  type ClinicalDecisionResponse,
  type ClinicalDecisionListResponse,
} from '../api/clinical_decision'

function confidenceBadge(confidence: string): string {
  switch (confidence?.toLowerCase()) {
    case 'high':
    case 'very high': return 'bg-green-100 text-green-800 border-green-200'
    case 'medium':
    case 'moderate': return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'low':
    case 'very low': return 'bg-red-100 text-red-800 border-red-200'
    default: return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function formatDateTime(iso: string): string {
  try { return new Date(iso).toLocaleString('zh-TW') } catch { return iso }
}

export default function ClinicalDecisionListPage() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<DatabasePatient[]>([])
  const [patientId, setPatientId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ClinicalDecisionListResponse | null>(null)

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

  async function selectPatient(id: string) {
    const normalized = id.trim()
    if (!normalized) return
    setPatientId(normalized)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await fetchClinicalDecisionsByPatientId(normalized))
      const url = new URL(window.location.href)
      url.searchParams.set('patientId', normalized)
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '查詢臨床決策失敗')
    } finally {
      setLoading(false)
    }
  }

  async function selectAdvancedPatient(value: string) {
    const normalized = value.trim()
    if (!normalized) return
    setLoading(true)
    setError(null)
    try {
      const patient = await getDatabasePatient(normalized)
      setPatients((current) => current.some((item) => item.patient_id === patient.patient_id) ? current : [patient, ...current].slice(0, 100))
      await selectPatient(patient.patient_id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '患者不存在')
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-xl text-gray-400 hover:text-primary-600">←</button>
        <div><p className="text-sm font-semibold text-primary-600">Clinical Decision</p><h1 className="text-3xl font-bold">臨床決策列表</h1><p className="mt-1 text-gray-600">最近 100 位患者快速選擇，或以完整 Patient ID 精準查詢。</p></div>
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

      {!loading && result && result.decisions.length === 0 && <section className="mt-6 rounded-xl border bg-white p-12 text-center text-gray-400">所選患者目前沒有臨床決策記錄。</section>}

      {!loading && result && result.decisions.length > 0 && (
        <section className="mt-6 overflow-hidden rounded-xl border bg-white shadow-sm">
          <div className="flex items-center justify-between border-b px-5 py-4"><h2 className="font-semibold">{patientId} 的決策</h2><span className="text-xs text-gray-400">最多展示 100 筆 · 共 {result.total ?? result.decisions.length} 筆</span></div>
          <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs uppercase text-gray-500"><tr><th className="px-5 py-3">決策類型</th><th className="px-5 py-3">信心等級</th><th className="px-5 py-3">Patient ID</th><th className="px-5 py-3">建立時間</th><th className="px-5 py-3">操作</th></tr></thead><tbody className="divide-y">{result.decisions.slice(0, 100).map((decision: ClinicalDecisionResponse) => <tr key={decision.decision_id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/clinical-decision/${decision.decision_id}`)}><td className="px-5 py-4 font-medium">{decision.decision_type || '—'}</td><td className="px-5 py-4"><span className={`rounded-full border px-2.5 py-0.5 text-xs ${confidenceBadge(decision.confidence)}`}>{decision.confidence || '—'}</span></td><td className="px-5 py-4 font-mono text-xs">{decision.patient_id || '—'}</td><td className="px-5 py-4 text-gray-500">{decision.created_at ? formatDateTime(decision.created_at) : '—'}</td><td className="px-5 py-4 text-primary-600">查看詳情 →</td></tr>)}</tbody></table></div>
        </section>
      )}
    </main>
  )
}
