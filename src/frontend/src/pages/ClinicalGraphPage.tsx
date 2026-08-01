import { useEffect, useState } from 'react'

import { apiRequest } from '../api/client'
import {
  getDatabasePatient,
  listRecentDatabasePatients,
  patientDisplayLabel,
  type DatabasePatient,
} from '../api/databasePatients'
import DualModeSelector from '../components/DualModeSelector'

interface Entity {
  id: string
  kind: string
  name: string
  properties?: Record<string, unknown>
}

interface Relation {
  id: string
  kind: string
  from_id: string
  to_id: string
}

interface ThreadResponse {
  patient_id: string
  entities: Entity[]
  relations: Relation[]
  projection_status: string
  message?: string
}

export default function ClinicalGraphPage() {
  const [patients, setPatients] = useState<DatabasePatient[]>([])
  const [patientId, setPatientId] = useState('')
  const [advancedPatientId, setAdvancedPatientId] = useState('')
  const [data, setData] = useState<ThreadResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [advancedLoading, setAdvancedLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await listRecentDatabasePatients(100)
        setPatients(result.items)
        const requested = new URLSearchParams(window.location.search).get('patientId')
        const initial = result.items.find((item) => item.patient_id === requested) || result.items[0]
        if (initial) {
          setPatientId(initial.patient_id)
          await loadGraph(initial.patient_id)
        } else if (requested) {
          setAdvancedPatientId(requested)
          await selectAdvancedPatient(requested)
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '無法載入患者資料')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  async function loadGraph(id: string) {
    const normalized = id.trim()
    if (!normalized) return
    setLoading(true)
    setError(null)
    setData(null)
    try {
      setData(await apiRequest<ThreadResponse>(`/clinical-graph/patient/${encodeURIComponent(normalized)}/thread`))
      const url = new URL(window.location.href)
      url.searchParams.set('patientId', normalized)
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法載入知識圖譜')
    } finally {
      setLoading(false)
    }
  }

  async function selectAdvancedPatient(value = advancedPatientId) {
    const normalized = value.trim()
    if (!normalized) return
    setAdvancedLoading(true)
    setError(null)
    try {
      const patient = await getDatabasePatient(normalized)
      setPatientId(patient.patient_id)
      setPatients((current) => current.some((item) => item.patient_id === patient.patient_id)
        ? current
        : [patient, ...current].slice(0, 100))
      await loadGraph(patient.patient_id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '患者不存在')
    } finally {
      setAdvancedLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">Clinical Knowledge Graph</p>
        <h1 className="text-3xl font-bold">臨床知識圖譜</h1>
        <p className="mt-2 text-gray-600">預設從資料庫最近 100 位患者中選擇；也可輸入完整 Patient ID 精準查詢整個資料庫。</p>
      </header>

      {error && <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-red-700">{error}</div>}

      <DualModeSelector
        title="選擇患者"
        description="一般模式顯示最近 100 位患者；進階模式可用完整 Patient ID 查詢整個資料庫。"
        recentContent={(
          <div className="p-4">
            <label className="block text-sm font-medium text-slate-700">
              最近 100 位患者
              <select
                aria-label="最近 100 位患者"
                className="mt-2 w-full rounded-lg border px-3 py-2"
                value={patientId}
                disabled={loading || patients.length === 0}
                onChange={(event) => {
                  setPatientId(event.target.value)
                  void loadGraph(event.target.value)
                }}
              >
                {patients.map((patient) => (
                  <option key={patient.patient_id} value={patient.patient_id}>{patientDisplayLabel(patient)}</option>
                ))}
              </select>
            </label>
            {patients.length === 0 && !loading && <p className="mt-2 text-sm text-slate-500">目前沒有患者資料。</p>}
          </div>
        )}
        advancedLabel="完整 Patient ID"
        advancedPlaceholder="輸入完整 UUID Patient ID"
        advancedValue={advancedPatientId}
        onAdvancedValueChange={setAdvancedPatientId}
        onAdvancedSubmit={() => selectAdvancedPatient()}
        advancedLoading={advancedLoading}
        advancedHelp="精準查詢成功後會載入同一個知識圖譜結果區，並同步 patientId 到網址。"
      />

      {loading && !data && <div className="mt-6 rounded-xl border bg-white p-10 text-center text-gray-500">載入中…</div>}

      {data && (
        <section className="mt-6 space-y-5 rounded-xl border bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
            <div><h2 className="text-xl font-bold">Patient Thread: {data.patient_id}</h2><p className="text-sm text-gray-500">Projection: {data.projection_status}</p></div>
            <div className="flex gap-2 text-sm"><span className="rounded bg-indigo-50 px-3 py-1 text-indigo-700">{data.entities.length} entities</span><span className="rounded bg-emerald-50 px-3 py-1 text-emerald-700">{data.relations.length} relations</span></div>
          </div>
          {data.message && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-amber-800">{data.message}</p>}
          <div className="grid gap-5 lg:grid-cols-2">
            <section><h3 className="font-bold">Entities</h3><div className="mt-2 max-h-[560px] space-y-2 overflow-y-auto">{data.entities.slice(0, 100).map((entity) => <article key={entity.id} className="rounded border p-3 text-sm"><strong>{entity.kind}</strong><div>{entity.name}</div><div className="text-xs text-gray-400">{entity.id}</div></article>)}</div></section>
            <section><h3 className="font-bold">Relations</h3><div className="mt-2 max-h-[560px] space-y-2 overflow-y-auto">{data.relations.slice(0, 100).map((relation) => <article key={relation.id} className="rounded border p-3 text-sm"><strong>{relation.kind}</strong><div className="mt-1 break-all text-xs text-gray-500">{relation.from_id} → {relation.to_id}</div></article>)}</div></section>
          </div>
        </section>
      )}
    </main>
  )
}
