import type { PTCResearchCase } from './ptcResearch'

const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`)
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

export interface PTCLatestCase extends PTCResearchCase {
  created_at?: string
  updated_at?: string
}

export interface PTCLatestCasesResponse {
  count: number
  limit: number
  cases: PTCLatestCase[]
}

export interface PTCProteinStructure {
  gene: string
  name: string
  uniprot: string
  alphafold_entry_id: string
  alphafold_entry_url: string
  cif_url: string
  pdb_url?: string
  confidence_url?: string
  experimental_pdb_ids: string[]
  default_pdb_id?: string
  source: string
  disclaimer: string
}

export function getLatestPTCCases(limit = 100): Promise<PTCLatestCasesResponse> {
  return request(`/ptc-visualization/cases/latest?limit=${Math.min(100, Math.max(1, limit))}`)
}

export function getPTCProteinStructure(gene: string): Promise<PTCProteinStructure> {
  return request(`/ptc-visualization/proteins/${encodeURIComponent(gene)}`)
}
