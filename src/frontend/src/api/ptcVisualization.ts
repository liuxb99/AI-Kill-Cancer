import { apiRequest, withQuery } from './client'
import type { PTCResearchCase } from './ptcResearch'

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
  return apiRequest(withQuery('/ptc-visualization/cases/latest', {
    limit: Math.min(100, Math.max(1, limit)),
  }))
}

export function getPTCProteinStructure(gene: string): Promise<PTCProteinStructure> {
  return apiRequest(`/ptc-visualization/proteins/${encodeURIComponent(gene)}`)
}
