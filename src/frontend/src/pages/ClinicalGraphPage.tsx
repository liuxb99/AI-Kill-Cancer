import { useEffect, useState } from 'react'

import DualModeSelector from '../components/DualModeSelector'
import {
  getDatabasePatient,
  listRecentDatabasePatients,
  patientDisplayLabel,
  type DatabasePatient,
} from '../api/databasePatients'

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
  const [data, setData] = useState<ThreadResponse | null>(null)
  const [loading, setLoading] = useState(true)
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
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`/api/v1/clinical-graph/patient/${encodeURIComponent(normalized)}/thread`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
        throw new Error(body.detail || 'Patient graph data not found or projection pending')
      }
      setData(await response.json())
      const url = new URL(window.location.href)
      url.searchParams.set('patientId', normalized)
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '無法載入知識圖譜')
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
      setPatientId(patient.patient_id)
      setPatients((current) => current.some((item) => item.patient_id === patient.patient_id) ? current : [patient, ...current].slice(0, 100))
      await loadGraph(patient.patient_id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '患者不存在')
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <header className="mb-6">
        <p className="text-sm font-semibold text-indigo-600">Clinical Knowledge Graph</p>
        <h1 className="text-3xl font-bold">臨床知識圖譜</h1>
        <p className="mt-2 text-gray-600">預設從資料庫最近 100 位患者中選擇；也可輸入完整 Patient ID 精準查詢整個資料庫。</p>
      </header>

      <DualModeSelector
        items={patients}
        selectedId={patientId}
        onSelect={(id) => { setPatientId(id); void loadGraph(id) }}
        getId={(item) => item.patient_id}
        getLabel={patientDisplayLabel}
        listLabel="最近 100 位患者"
        queryLabel="完整 Patient ID"
        queryPlaceholder="輸入完整 UUID Patient ID"
        onAdvancedQuery={selectAdvancedPatient}
        loading={loading}
        error={error}
      />

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
