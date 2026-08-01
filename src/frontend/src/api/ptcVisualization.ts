import type { PTCResearchCase } from './ptcResearch'

/**
 * PTC pages are served by the same Vercel deployment as the API proxy.
 * Always use a same-origin relative URL here. A malformed VITE_API_URL (for
 * example a quoted value or a value containing whitespace) makes iOS Safari
 * throw `The string did not match the expected pattern.` before fetch starts.
 */
const API_PREFIX = '/api/v1'

async function request<T>(path: string): Promise<T> {
  const url = `${API_PREFIX}${path.startsWith('/') ? path : `/${path}`}`
  let response: Response
  try {
    response = await fetch(url)
  } catch (reason) {
    const message = reason instanceof Error ? reason.message : String(reason)
    throw new Error(`PTC API request failed (${url}): ${message}`)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body)
    throw new Error(detail || `HTTP ${response.status}`)
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

export interface PTCExperimentalStructure {
  pdb_id: string
  pdb_url: string
  entry_url: string
}

export interface PTCProteinStructure {
  gene: string
  name: string
  uniprot: string
  alphafold_entry_id: string
  alphafold_entry_url: string
  cif_url: string
  cif_urls: string[]
  pdb_url: string
  pdb_urls: string[]
  experimental_structures: PTCExperimentalStructure[]
  experimental_pdb_ids: string[]
  default_pdb_id?: string
  renderer: 'builtin-threejs-pdb'
  uses_alphafold_api: false
  source: string
  disclaimer: string
}

export function getLatestPTCCases(limit = 100): Promise<PTCLatestCasesResponse> {
  return request(`/ptc-visualization/cases/latest?limit=${Math.min(100, Math.max(1, limit))}`)
}

export function getPTCProteinStructure(gene: string): Promise<PTCProteinStructure> {
  return request(`/ptc-visualization/proteins/${encodeURIComponent(gene)}`)
}
