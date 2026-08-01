export interface DatabasePatient {
  patient_id: string
  external_id?: string | null
  name?: string | null
  sex?: string | null
  birth_date?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface DatabasePatientList {
  items: DatabasePatient[]
  total: number
  skip: number
  limit: number
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { headers: authHeaders() })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export function listRecentDatabasePatients(limit = 100): Promise<DatabasePatientList> {
  return request(`/patients?skip=0&limit=${Math.min(Math.max(limit, 1), 100)}`)
}

export function getDatabasePatient(patientId: string): Promise<DatabasePatient> {
  return request(`/patients/${encodeURIComponent(patientId.trim())}`)
}

export function patientDisplayLabel(patient: DatabasePatient): string {
  const id = patient.patient_id || patient.external_id || 'unknown'
  const details = [patient.external_id && patient.external_id !== id ? patient.external_id : null, patient.sex].filter(Boolean)
  return details.length ? `${id} · ${details.join(' · ')}` : id
}
