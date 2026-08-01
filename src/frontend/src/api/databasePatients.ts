interface RawDatabasePatient {
  id: string
  external_id?: string | null
  display_name?: string | null
  birth_year?: number | null
  age_range?: string | null
  sex?: string | null
  consent_status?: string | null
  created_at?: string | null
  updated_at?: string | null
}

interface RawDatabasePatientList {
  items: RawDatabasePatient[]
  total: number
  skip: number
  limit: number
}

export interface DatabasePatient {
  patient_id: string
  external_id?: string | null
  display_name?: string | null
  birth_year?: number | null
  age_range?: string | null
  sex?: string | null
  consent_status?: string | null
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

function normalizePatient(patient: RawDatabasePatient): DatabasePatient {
  return {
    patient_id: patient.id,
    external_id: patient.external_id,
    display_name: patient.display_name,
    birth_year: patient.birth_year,
    age_range: patient.age_range,
    sex: patient.sex,
    consent_status: patient.consent_status,
    created_at: patient.created_at,
    updated_at: patient.updated_at,
  }
}

export async function listRecentDatabasePatients(limit = 100): Promise<DatabasePatientList> {
  const result = await request<RawDatabasePatientList>(`/patients?skip=0&limit=${Math.min(Math.max(limit, 1), 100)}`)
  return { ...result, items: result.items.map(normalizePatient) }
}

export async function getDatabasePatient(patientId: string): Promise<DatabasePatient> {
  return normalizePatient(await request<RawDatabasePatient>(`/patients/${encodeURIComponent(patientId.trim())}`))
}

export function patientDisplayLabel(patient: DatabasePatient): string {
  const details = [patient.display_name, patient.external_id, patient.sex, patient.age_range].filter(Boolean)
  return details.length ? `${patient.patient_id} · ${details.join(' · ')}` : patient.patient_id
}
